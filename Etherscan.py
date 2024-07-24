import requests
import csv
from datetime import datetime
import os
from web3 import Web3
from req_bot import send_message

# Загрузка переменных окружения
import load_env

path_to_file = os.getenv('PATH_TO_FILE')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
CONTRACT_ADDRESS_TETHER = os.getenv('CONTRACT_ADDRESS_TETHER')
CONTRACT_ADDRESS_TETHER_BAN = os.getenv('CONTRACT_ADDRESS_TETHER_BAN')
INFURA_URL = os.getenv('INFURA_PROJECT_URL')  # Замените на ваш Infura Project ID
TARGET_TOPIC = '0x42e160154868087d6bfdc0ca23d96a1c1cfa32f1b72ba9ba27b69b98a0d819dc'
blockchainlink = 'https://etherscan.io/address/'
token = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Инициализация Web3
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Проверка соединения
if not web3.is_connected():
    print("Не удалось подключиться к узлу Ethereum")
    exit()

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

def get_usdc_balance(wallet_address):
    wallet_address = Web3.to_checksum_address(wallet_address)
    usdc_contract = web3.eth.contract(address=CONTRACT_ADDRESS_TETHER, abi=[
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        }
    ])
    balance = usdc_contract.functions.balanceOf(wallet_address).call() / 1000000
    balance = round(balance, 3)
    return balance

# Функция для проверки логов транзакции на наличие целевого топика
def check_logs_for_topic(tx_hash, target_topic):
    try:
        receipt = web3.eth.get_transaction_receipt(tx_hash)
        logs = receipt['logs']

        block_wallet_flag = False
        topik_list = []
        address_list = []
        block_wallet = ''

        for log in logs:
            hex_data = log['data'].hex()
            address = '0x' + hex_data[-40:]
            address_list.append(address)

            for topic in log['topics']:
                topic = topic.hex()
                if target_topic == topic:
                    block_wallet_flag = True
                    block_wallet = address
                    print(f'Правильный формат адреса: {block_wallet}')
                    if block_wallet == '0x0x':
                        block_wallet = log['topics'][1].hex()
                        block_wallet = '0x' + block_wallet[-40:]
                        print(f'Неправильный формат адреса: {block_wallet}')
                topik_list.append(topic)

        return block_wallet_flag, block_wallet, topik_list, address_list

    except Exception as e:
        print(f"Ошибка при обработке транзакции {tx_hash}: {e}")
        return False, '', [], []

# Основной процесс
def main():
    start_block, blocked_wallets_count, total_usdc_balance = get_last_block(CONTRACT_ADDRESS_TETHER_BAN)
    curent_block = start_block + 1
    end_block = 99999999

    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={CONTRACT_ADDRESS_TETHER_BAN}&startblock={curent_block}&endblock={end_block}&sort=asc&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url)
    data = response.json()

    if data['status'] == '1':
        transactions = data['result']

        # Определение заголовков CSV файла
        csv_headers = ["blockNumber", "timeStamp", "timestamp_utc", "hash", "log_flag", "block wallet", "blocked wallet balance", "topik list", "address in topik"]

        # Сохранение транзакций в CSV файл
        csv_file = f"{path_to_file}{CONTRACT_ADDRESS_TETHER_BAN}.csv"
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=csv_headers)
            if os.stat(csv_file).st_size == 0:
                writer.writeheader()


            for tx in transactions:
                timestamp_utc = datetime.utcfromtimestamp(int(tx["timeStamp"])).strftime('%Y-%m-%d %H:%M:%S')
                tx_data = {
                    "blockNumber": tx["blockNumber"],
                    "timeStamp": tx["timeStamp"],
                    "timestamp_utc": timestamp_utc,
                    "hash": tx["hash"]
                }
                # Проверка логов транзакции и добавление флага
                block_wallet_flag, block_wallet, topik_list, address_list = check_logs_for_topic(tx["hash"], TARGET_TOPIC)
                tx_data["blocked wallet balance"] = ''
                tx_data["log_flag"] = block_wallet_flag
                tx_data["block wallet"] = block_wallet
                tx_data["topik list"] = topik_list
                tx_data["address in topik"] = address_list

                if block_wallet:
                    blocked_wallet_balance = get_usdc_balance(block_wallet)
                    tx_data["blocked wallet balance"] = blocked_wallet_balance
                    blocked_wallets_count = blocked_wallets_count + 1
                    total_usdc_balance = total_usdc_balance + blocked_wallet_balance

                    send_message(token, block_wallet, timestamp_utc, blocked_wallet_balance, blockchainlink, CONTRACT_ADDRESS_TETHER_BAN, blocked_wallets_count, total_usdc_balance)

                writer.writerow(tx_data)


        print(f"Транзакции для адреса {CONTRACT_ADDRESS_TETHER_BAN} сохранены в файл {csv_file}")
    else:
        print(f"Ошибка получения транзакций для адреса {CONTRACT_ADDRESS_TETHER_BAN}: {data['message']}")

if __name__ == '__main__':
    main()

