import base58
import binascii
import hashlib

import requests
import os
import csv
from datetime import datetime
from req_bot import send_message

import load_env

path_to_file = os.getenv('PATH_TO_FILE')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADRESS_TETHER_TRC20')
CONTRACT_ADDRESS_BAN = os.getenv('CONTRACT_ADRESS_TETHER_TRC20_BAN')
blockchainlink = 'https://tronscan.org/#/address/'
token = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Функция для конвертации hex формата логов в обычный адрес
def tron_wallet_decoder(hex_address):
    if hex_address.startswith('0x'):
        hex_address = '41' + hex_address[2:]

    if not hex_address.startswith('0x') and not hex_address.startswith('41'):
        print("Неправильный формат адреса:", hex_address)
        exit()

    # Преобразуем hex-строку в байты
    decoded_bytes = binascii.unhexlify(hex_address)

    # Добавляем контрольную сумму
    checksum = hashlib.sha256(hashlib.sha256(decoded_bytes).digest()).digest()[:4]
    address_with_checksum = decoded_bytes + checksum

    # Кодируем байты в Base58
    base58_address = base58.b58encode(address_with_checksum).decode('utf-8')
    return base58_address

# Функция для получения баланса Тезер из TronGrid по адресу кошелька
def get_blocked_wallet_balance(wallet_address):
    url = f"https://api.trongrid.io/v1/accounts/{wallet_address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tether_balance = 0
        try:
            trc20_data = data['data'][0]['trc20']
            for balance_trx20 in trc20_data:
                if CONTRACT_ADDRESS in balance_trx20.keys():
                    tether_balance = balance_trx20[CONTRACT_ADDRESS]

            return round(float(tether_balance), 3) / 1000000
        except (IndexError, KeyError) as e:
            print(f"Нет токенов по адресу {wallet_address}: {e}")
            return tether_balance
    else:
        print(f"Ошибка при запросе TronGrid API: {response.status_code} {response.text}")
        return None

def get_last_block(tron_sc):
    """Читает последнюю строку из CSV-файла и возвращает значение последнего блока блокчейна."""
    csv_file = f"{path_to_file}{tron_sc}.csv"
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

def transactions_info(transaction):
    blocked_wallet = ''
    log_flag = ''
    event_list = []
    base_url = "https://api.trongrid.io"

    response = requests.get(f"{base_url}/v1/transactions/{transaction}/events")
    if response.status_code != 200:
        print("Ошибка получения данных:", response.status_code, response.text)
        exit()

    data = response.json()
    transaction = data.get('data', [])

    for tx in transaction:
        if tx['event_name'] == 'AddedBlackList':
            blocked_wallet = tron_wallet_decoder(tx['result']['_user'])
            log_flag = True
        event_list.append(tx['event_name'])

    return log_flag, blocked_wallet, event_list

def main():
    start_block, blocked_wallets_count, total_usdc_balance = get_last_block(CONTRACT_ADDRESS_BAN)

    base_url = "https://api.trongrid.io"

    params = {
        'limit': 200,  # Ограничиваем запрос до 200 транзакций за раз
        'order_by': 'block_timestamp,desc'
    }

    response = requests.get(f"{base_url}/v1/accounts/{CONTRACT_ADDRESS_BAN}/transactions", params=params)

    if response.status_code != 200:
        print("Ошибка получения данных:", response.status_code, response.text)
        exit()

    data = response.json()

        # Определение заголовков CSV файла
    csv_headers = ["blockNumber", "timestamp", "timestamp_utc", "tx_id", "log_flag", "blocked_wallet", "blocked_wallet_balance", "event_list"]

    # Сохранение транзакций в CSV файл
    csv_file = f"{path_to_file}{CONTRACT_ADDRESS_BAN}.csv"
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=csv_headers)
        if os.stat(csv_file).st_size == 0:
            writer.writeheader()

        transactions = data.get('data', [])
        trx_list = []

        if not transactions:
            print(f"Ошибка получения данных: Пустые данные {response.url}")
            exit()
        for tx in transactions:
            try:
                if tx['blockNumber'] > start_block:
                    transactions_data = transactions_info(tx['txID'])
                    log_flag, blocked_wallet, event_list = transactions_data
                    blocked_wallet_balance = ''
                    timestamp = tx["block_timestamp"] / 1000
                    timestamp_utc = datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
                    if blocked_wallet:
                        blocked_wallet_balance = get_blocked_wallet_balance(blocked_wallet)
                    tx_element = {'blockNumber': tx['blockNumber'],
                                  'timestamp': timestamp,
                                  'timestamp_utc': timestamp_utc,
                                  'tx_id': tx['txID'],
                                  'log_flag': log_flag,
                                  'blocked_wallet': blocked_wallet,
                                  'blocked_wallet_balance': blocked_wallet_balance,
                                  'event_list': event_list}

                    trx_list.append(tx_element)
            except:
                continue

        if not trx_list:
            print("Нет транзакций")
            exit()
        trx_sorted_list = sorted(trx_list, key=lambda x: x['blockNumber'])
        for write_row in trx_sorted_list:
            if write_row['log_flag']:
                send_message(token, write_row['blocked_wallet'], write_row['timestamp_utc'], write_row['blocked_wallet_balance'], blockchainlink,
                             CONTRACT_ADDRESS,
                             blocked_wallets_count, total_usdc_balance)
            writer.writerow(write_row)

if __name__ == '__main__':
    main()


