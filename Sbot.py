import discord
from discord import app_commands
import math
import os
import re
from flask import Flask
from threading import Thread

# インテント設定
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ランクごとの基本係数
RANK_MULTIPLIERS = {
    'F': 2.45,
    'E': 2.5,
    'D': 2.55,
    'C': 2.6,
    'B': 2.65,
    'A': 2.7,
    'S': 2.75
}

# 祝福の宝石価格（初期値。メッセージで誰でも変更可能）
BLESSING_GEM_PRICE = 1070

# 係数補正関数（+3以下 +0.05、+6〜+8 -0.05、+9以上 -0.10）
def get_adjusted_multiplier(rank, current_level):
    base = RANK_MULTIPLIERS[rank]
    if current_level <= 3:
        return base + 0.05
    elif current_level <= 5:
        return base  # +4〜+5は補正なし
    elif current_level <= 8:
        return base - 0.05
    else:  # +9以上
        return base - 0.10

@client.event
async def on_ready():
    print(f"ログイン成功！ あるけみすと装備相場Bot")
    print(f"名前: {client.user}")
    await tree.sync()
    print("スラッシュコマンド同期完了")

# おまけ /hello
@tree.command(name="hello", description="挨拶＋現在の宝石価格確認")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"ちくわだよ〜！\n"
        f"祝福の宝石現在価格: **{BLESSING_GEM_PRICE:,} マー**\n"
        f"変更したい時は「祝福1200」みたいに送ってね！（誰でもOK）",
        ephemeral=True
    )

# メイン処理
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip().upper()

    # 祝福価格変更コマンド（誰でもOK）
    if content.startswith("祝福"):
        match = re.search(r"祝福(\d+)", content)
        if match:
            try:
                new_price = int(match.group(1))
                if new_price < 0:
                    await message.channel.send("価格は0以上でお願い！")
                    return
                global BLESSING_GEM_PRICE
                old = BLESSING_GEM_PRICE
                BLESSING_GEM_PRICE = new_price
                await message.channel.send(
                    f"祝福の宝石価格を **{old:,} → {new_price:,} マー** に更新しました！"
                )
            except:
                await message.channel.send("「祝福」+数字でお願い（例: 祝福1090）")
        return

    # 相場計算
    if len(content) < 3 or '+' not in content or content[0] not in RANK_MULTIPLIERS:
        return

    try:
        rank = content[0]
        rest = content[1:]
        price_str, plus_str = rest.split('+', 1)
        base_price = int(price_str)
        target_plus = int(plus_str)

        if target_plus < 0:
            await message.channel.send("強化値は0以上で！")
            return

        # 通常相場
        normal = float(base_price)
        normal_steps = [f"+0: {base_price}"]
        for lv in range(1, target_plus + 1):
            coeff = get_adjusted_multiplier(rank, lv)
            normal *= coeff
            normal_steps.append(f"+{lv}: {normal:.0f} × {coeff:.2f} = {normal:.0f}")

        normal_price = round(normal)

        # 宝石使用相場
        gem = float(base_price)
        gem_steps = [f"+0: {base_price}"]
        gem_count = 0

        for lv in range(1, target_plus + 1):
            coeff = get_adjusted_multiplier(rank, lv)
            mul = gem * coeff

            if lv <= 3:
                gem_val = gem + BLESSING_GEM_PRICE
                chosen = min(mul, gem_val)
                if chosen == gem_val:
                    gem_count += 1
                    gem_steps.append(f"+{lv}: {gem:.0f} + {BLESSING_GEM_PRICE} = {chosen:.0f} (宝石)")
                else:
                    gem_steps.append(f"+{lv}: {gem:.0f} × {coeff:.2f} = {chosen:.0f}")
            else:
                chosen = mul
                gem_steps.append(f"+{lv}: {gem:.0f} × {coeff:.2f} = {chosen:.0f}")
            gem = chosen

        gem_price = round(gem)

        # 安い方をメイン表示
        if gem_price < normal_price:
            main_p = gem_price
            main_t = f"宝石{gem_count}個使用"
            sub_p = normal_price
            sub_t = "通常"
            steps = gem_steps
        else:
            main_p = normal_price
            main_t = "通常"
            sub_p = gem_price
            sub_t = f"宝石{gem_count}個使用"
            steps = normal_steps

        # 応答
        res = f"**{rank}{base_price}+{target_plus} の相場**\n"
        res += f"→ **{main_p:,} マー** （{main_t}）\n"
        if sub_p != main_p:
            res += f"　　（もう一方: {sub_p:,} マー）\n\n"

        res += "【詳細ステップ】\n" + "\n".join(steps) + "\n"
        res += f"最終: {main_p:,} マー"

        await message.channel.send(res)

    except ValueError:
        await message.channel.send("入力形式が変かも…例: S500+4 や 祝福1090")
    except Exception as e:
        await message.channel.send(f"エラー: {str(e)}")

# FlaskでKoyebの健康チェック対応
app = Flask(__name__)

@app.route('/')
def home():
    return "ちくわ相場Bot is alive!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8000)

Thread(target=run_flask).start()

# トークンは環境変数から取得（KoyebのEnvironment variablesで設定）
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("警告: 環境変数 TOKEN が設定されていません")
    exit(1)

client.run(TOKEN)