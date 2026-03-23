import discord
from discord import app_commands
import os
import re
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

RANK_MULTIPLIERS = {
    'F': 2.45, 'E': 2.5, 'D': 2.55, 'C': 2.6,
    'B': 2.65, 'A': 2.7, 'S': 2.75
}

BLESSING_GEM_PRICE = 1070

def get_adjusted_multiplier(rank, current_level, is_special=False):
    base = RANK_MULTIPLIERS[rank]
    if is_special:
        return base - 0.10
    if current_level <= 3:
        return base + 0.05
    elif current_level <= 5:
        return base
    elif current_level <= 8:
        return base - 0.05
    else:
        return base - 0.10

@client.event
async def on_ready():
    print(f"ログイン成功！ あるけみすと装備相場Bot")
    print(f"名前: {client.user}")
    await tree.sync()

@tree.command(name="hello", description="挨拶＋宝石価格確認")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"ふむ、元気そうだな。何か食べていくか?\n"
        f"祝福の宝石現在価格は **{BLESSING_GEM_PRICE:,} マー**",
        ephemeral=True
    )

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    # 祝福価格変更
    if content.upper().startswith("祝福"):
        match = re.search(r"祝福(\d+)", content.upper())
        if match:
            try:
                new_price = int(match.group(1))
                if new_price >= 0:
                    global BLESSING_GEM_PRICE
                    old = BLESSING_GEM_PRICE
                    BLESSING_GEM_PRICE = new_price
                    await message.channel.send(f"宝石価格 {old:,} → {new_price:,} マーに更新！")
            except:
                pass
        return

    # 相場計算（全角＋・スペース対応）
    clean_content = re.sub(r'\s+', '', content.upper()).replace('＋', '+')

    if len(clean_content) < 3 or '+' not in clean_content or clean_content[0] not in RANK_MULTIPLIERS:
        return

    # 「お得」検知（大幅強化）
    is_special = any(x in content for x in ["お得", "オトク", "おとく"])

    print(f"受信: {content} | お得検知: {is_special}")  # デバッグ用

        try:
        rank = clean_content[0]
        rest = clean_content[1:]

        # + で分割前に「お得」部分を切り落とす（数字だけ残す）
        # 数字の後ろに文字が入ってたら切り落とし
        plus_index = rest.find('+')
        if plus_index == -1:
            return

        price_str = rest[:plus_index]
        after_plus = rest[plus_index+1:]

        # after_plus から数字だけ抜き出す（お得などが付いててもOK）
        plus_str = ''.join(c for c in after_plus if c.isdigit())

        base_price = int(price_str)
        target_plus = int(plus_str) if plus_str else 0

        if target_plus < 0:
            return

        # 以降の計算は同じ
        # ...（normal = float(base_price) から最後までそのまま）

        # 通常相場
        normal = float(base_price)
        normal_steps = [f"+0: {base_price}"]
        for lv in range(1, target_plus + 1):
            coeff = get_adjusted_multiplier(rank, lv, is_special)
            normal *= coeff
            normal_steps.append(f"+{lv}: {normal:.0f} × {coeff:.2f} = {normal:.0f}")

        normal_price = round(normal)

        # 宝石使用相場（is_special適用）
        gem = float(base_price)
        gem_steps = [f"+0: {base_price}"]
        gem_count = 0

        for lv in range(1, target_plus + 1):
            coeff = get_adjusted_multiplier(rank, lv, is_special)
            mul = gem * coeff

            if lv <= 3:
                chosen = min(mul, gem + BLESSING_GEM_PRICE)
                if chosen == gem + BLESSING_GEM_PRICE:
                    gem_count += 1
                    gem_steps.append(f"+{lv}: {gem:.0f} + {BLESSING_GEM_PRICE} = {chosen:.0f} (宝石)")
                else:
                    gem_steps.append(f"+{lv}: {gem:.0f} × {coeff:.2f} = {chosen:.0f}")
            else:
                chosen = mul
                gem_steps.append(f"+{lv}: {gem:.0f} × {coeff:.2f} = {chosen:.0f}")
            gem = chosen

        gem_price = round(gem)

        # 安い方を返す
        if gem_price < normal_price:
            main_p = gem_price
            main_t = f"宝石{gem_count}個使用"
            steps = gem_steps
        else:
            main_p = normal_price
            main_t = "通常"
            steps = normal_steps

        res = f"**{rank}{base_price}+{target_plus} の相場**\n"
        res += f"→ **{main_p:,} マー** （{main_t}）\n"
        res += "【詳細ステップ】\n" + "\n".join(steps) + "\n"
        res += f"最終: {main_p:,} マー"

        await message.channel.send(res)

    except Exception as e:
        print(f"エラー: {e}")  # ログに残すだけ
        return

# Flask（健康チェック）
app = Flask(__name__)

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8000)

Thread(target=run_flask).start()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("TOKEN未設定")
    exit(1)

client.run(TOKEN)