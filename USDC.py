import requests
import csv
from datetime import datetime
import os
from web3 import Web3
from req_bot import send_message

import load_env
path_to_file = os.getenv('PATH_TO_FILE')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADRESS_TETHER_USDC')
INFURA_URL = os.getenv('INFURA_PROJECT_URL')  # Замените на ваш Infura Project ID
TOPIC = "0xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855"
blockchainlink = 'https://etherscan.io/address/'
token = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')


# Инициализация Web3
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Проверка соединения
if not web3.is_connected():
    print("Не удалось подключиться к узлу Ethereum")
    exit()

def save_dex_trasformator(value):
    try:
        return int(value, 16)
    except ValueError:
        0

# Функция для получения последнего блока из CSV
def get_last_block(ethereum_sc):
    """Читает последнюю строку из CSV-файла и возвращает значение последнего блока блокчейна."""
    csv_file = f"{path_to_file}{ethereum_sc}.csv"
    if not os.path.exists(csv_file):
        return 0, 0, 0  # Возвращает 0, если файл не существует
    with open(csv_file, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        blocked_wallets_count = 0
        total_usdc_balance = 0
        last_row = None
        for row in reader:
            last_row = row
            if row['log_flag'] == 'True':
                blocked_wallets_count += 1
                total_usdc_balance += float(row['blocked wallet balance'].replace(',', '.'))
        if last_row:
            return int(last_row['blockNumber']), int(blocked_wallets_count), float(total_usdc_balance)
        return 0, 0, 0 # Возвращает 0, если файл пуст или не содержит блоков

# Функция для получения баланса USDC
def get_usdc_balance(wallet_address):
    wallet_address = Web3.to_checksum_address(wallet_address)
    usdc_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=[
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        }
    ])
    balance = usdc_contract.functions.balanceOf(wallet_address).call() / 10000
    return balance / 1e2  # USDC имеет 2

# Основной процесс
def main():
    last_block, blocked_wallets_count, total_usdc_balance = get_last_block(CONTRACT_ADDRESS)
    start_block = last_block + 1
    end_block = "latest"

    url = "https://api.etherscan.io/api"
    params = {
        "module": "logs",
        "action": "getLogs",
        "fromBlock": start_block,
        "toBlock": end_block,
        "address": CONTRACT_ADDRESS,
        "topic0": TOPIC,
        "apikey": ETHERSCAN_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()


    if data['status'] == '1':
        transactions = data['result']

        # Определение заголовков CSV файла
        csv_headers = ["blockNumber", "timeStamp", "timestamp_utc", "hash", "transactionIndex", "from", "to", "log_flag", "block wallet", "topik list", "adress in topik", "blocked wallet balance"]

        # Сохранение транзакций в CSV файл
        csv_file = f"{path_to_file}{CONTRACT_ADDRESS}.csv"
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            if os.stat(csv_file).st_size == 0:
                writer.writeheader()

            for tx in transactions:
                address_blocked_wallet = '0x' + tx['topics'][1][-40:]
                timestamp_utc = datetime.utcfromtimestamp(save_dex_trasformator(tx["timeStamp"])).strftime('%Y-%m-%d %H:%M:%S')
                usdc_balance = get_usdc_balance(address_blocked_wallet)
                tx_data = {
                    "blockNumber": save_dex_trasformator(tx["blockNumber"]),
                    "timeStamp": save_dex_trasformator(tx["timeStamp"]),
                    "timestamp_utc": timestamp_utc,
                    "hash": tx['transactionHash'],
                    "transactionIndex": save_dex_trasformator(tx["transactionIndex"]),
                    "from": "",  # Добавьте значение, если требуется
                    "to": "",    # Добавьте значение, если требуется
                    "log_flag": True,
                    "block wallet": address_blocked_wallet,
                    "topik list": tx['topics'][0],
                    "adress in topik": "",  # Добавьте значение, если требуется
                    "blocked wallet balance": usdc_balance
                }
                writer.writerow(tx_data)

                blocked_wallets_count = blocked_wallets_count + 1
                total_usdc_balance = total_usdc_balance + usdc_balance

                send_message(token, address_blocked_wallet, timestamp_utc, usdc_balance, blockchainlink, CONTRACT_ADDRESS,blocked_wallets_count, total_usdc_balance)

        print(f"Новые транзакции для адреса {CONTRACT_ADDRESS} сохранены в файл {csv_file}")
    else:
        print(f"Ошибка получения транзакций для адреса {CONTRACT_ADDRESS}: {data['message']}")


if __name__ == '__main__':
    main()
