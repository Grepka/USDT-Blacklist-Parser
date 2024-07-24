import requests
import os
import load_env

token = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
#-1002120526090


def send_message(token_bot, address_blocked_wallet, timestamp, balance, blockchainlink, contract, block_wallet_sum, block_wallet_sum_ballance):
    if contract == '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48':
        usdt_type = 'USDT (ERC20)'
        blockchain_type = 'Etherscan'
        sign = 'USDC'
    elif contract == '0xC6CDE7C39eB2f0F0095F41570af89eFC2C1Ea828':
        usdt_type = 'USDT (ERC20)'
        blockchain_type = 'Etherscan'
        sign = 'USDT Eth'
    elif contract == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t':
        usdt_type = 'USDT (TRC20)'
        blockchain_type = 'Tronscan'
        sign = 'USDT TRC'

    balance = round(balance, 3)
    block_wallet_sum_ballance = round(block_wallet_sum_ballance, 3) - 1

    balance = "{:,}".format(balance)
    block_wallet_sum_ballance = "{:,}".format(block_wallet_sum_ballance)

    message = (f"<code>{address_blocked_wallet}</code>\n"
               f"Time UTF: {timestamp}\n"
               f"Event:     AddedBlackList\n"
               f"Balance:   {balance} {usdt_type}\n"
               f"<a href='{blockchainlink}{address_blocked_wallet}'>{blockchain_type}</a>\n"
               f"Кошельков в бане {sign}: {block_wallet_sum}\n"
               f"Сумма в бане {sign}: {block_wallet_sum_ballance}\n"
               f"Не взаимодействуйте с данным адресом.")

    url = f'https://api.telegram.org/bot{token_bot}/sendMessage'
    params = {
        'chat_id': CHAT_ID,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
        'text': message
    }
    response = requests.get(url, params=params)

