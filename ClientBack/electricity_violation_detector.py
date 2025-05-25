import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import requests
from typing import Tuple, List, Dict, Optional
import time
import psycopg2  # Импорт для работы с PostgreSQL

# Конфигурация API
CLIENTS_API_URL = "http://127.0.0.1:8000/clients/get"
OVER_CONSUMERS_API_URL = "http://127.0.0.1:8001/over_consumers/batch"

# Конфигурация БД PostgreSQL (поменяй на свои данные)
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "141722"


def load_data_from_api() -> Tuple[Optional[np.ndarray], Optional[np.ndarray], List[str], List[Dict]]:
    try:
        response = requests.get(CLIENTS_API_URL)
        response.raise_for_status()
        raw_data = response.json().get("clients", [])

        if not raw_data:
            print("Получены пустые данные от API")
            return None, None, [], []

        X, y, addresses, full_data = [], [], [], []
        for entry in raw_data:
            consumption = entry.get("consumption", {})

            if isinstance(consumption, dict):
                consumption = list(consumption.values())

            if not consumption or len(consumption) < 3:
                continue

            last_months = consumption[-6:]
            avg_6 = np.mean(last_months)

            features = [
                avg_6,
                np.max(last_months),
                entry.get("residents_count", 0),
                entry.get("rooms_count", 0),
                entry.get("total_area", 0)
            ]
            X.append(features)
            y.append(1 if entry.get("is_commercial") else 0)
            addresses.append(entry.get("address", ""))

            entry['avg_consumption_6m'] = avg_6
            full_data.append(entry)

        if not X:
            print("Нет данных, удовлетворяющих условиям после фильтрации")
            return None, None, [], []

        return np.array(X), np.array(y), addresses, full_data

    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return None, None, [], []


def train_model(X: np.ndarray, y: np.ndarray) -> Tuple[tf.keras.Model, StandardScaler]:
    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        if len(X) < 10:
            raise ValueError("Недостаточно данных для обучения модели")

        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(X.shape[1],)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])

        model.compile(optimizer='adam',
                      loss='binary_crossentropy',
                      metrics=['accuracy'])

        model.fit(X_train, y_train,
                  epochs=20,
                  batch_size=32,
                  validation_split=0.2,
                  verbose=0)

        return model, scaler

    except Exception as e:
        print(f"Ошибка при обучении модели: {e}")
        raise


def load_complaints_addresses() -> List[str]:
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT complaint_address FROM complaints WHERE complaint_address IS NOT NULL;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        complaints_addresses = [row[0] for row in rows]
        return complaints_addresses
    except Exception as e:
        print(f"Ошибка при загрузке complaints из БД: {e}")
        return []


def detect_violators(model: tf.keras.Model, scaler: StandardScaler,
                     X: np.ndarray, addresses: List[str],
                     raw_data: List[Dict]) -> List[Dict]:
    try:
        complaints_addresses = load_complaints_addresses()
        complaints_set = set(complaints_addresses)

        X_scaled = scaler.transform(X)
        predictions = model.predict(X_scaled, verbose=0)

        violators = []
        for i, pred in enumerate(predictions):
            if raw_data[i].get("is_commercial", False):
                continue

            address = addresses[i]
            current_status = raw_data[i].get("is_checked")

            # Проверка на совпадение адреса с complaints — добавляем подозреваемого с приоритетом yellow
            if address in complaints_set:
                violator_data = {
                    "accountId": raw_data[i]["account_id"],
                    "address": address,
                    "priority": "yellow",
                    "isChecked": current_status if current_status else "no",
                    "avgConsumption6m": float(X[i][0])
                }
                violators.append(violator_data)
                continue

            if current_status in ["under_review", "no"]:
                avg_6 = X[i][0]
                priority = "red" if avg_6 > 6000 else "yellow"

                violator_data = {
                    "accountId": raw_data[i]["account_id"],
                    "address": address,
                    "priority": priority,
                    "isChecked": current_status,
                    "avgConsumption6m": float(avg_6)
                }
                violators.append(violator_data)

            elif current_status is None:
                avg_6 = X[i][0]
                if avg_6 > 3000:
                    priority = "red" if avg_6 > 6000 else "yellow"

                    violator_data = {
                        "accountId": raw_data[i]["account_id"],
                        "address": address,
                        "priority": priority,
                        "isChecked": "no",
                        "avgConsumption6m": float(avg_6)
                    }
                    violators.append(violator_data)

        return violators
    except Exception as e:
        print(f"Ошибка при определении нарушителей: {e}")
        return []


def send_violators_to_api(violators: List[Dict]) -> bool:
    if not violators:
        print("Нет нарушителей для отправки")
        return False

    try:
        delete_response = requests.delete("http://127.0.0.1:8001/over_consumers")
        delete_response.raise_for_status()

        response = requests.post(OVER_CONSUMERS_API_URL, json=violators)
        response.raise_for_status()
        print(f"Успешно отправлено {len(violators)} нарушителей")
        return True
    except Exception as e:
        print(f"Ошибка при отправке данных: {e}")
        return False


def main():
    print("Загрузка данных из API...")
    X, y, addresses, raw_data = load_data_from_api()

    if X is None or len(X) == 0:
        print("Не удалось загрузить данные или данные пусты. Завершение работы.")
        return

    print(f"Загружено {len(X)} записей. Обучение модели...")
    try:
        model, scaler = train_model(X, y)
    except Exception as e:
        print(f"Не удалось обучить модель: {e}")
        return

    print("Выявление нарушителей...")
    violators = detect_violators(model, scaler, X, addresses, raw_data)

    if violators:
        print("\n=== Нарушители ===")
        for violator in violators[:10]:
            print(
                f"ID: {violator['accountId']} | Адрес: {violator['address']} | Среднее потребление: {violator['avgConsumption6m']:.2f} кВт | Приоритет: {violator['priority']}")
        if len(violators) > 10:
            print(f"... и еще {len(violators) - 10} нарушителей")

        print("\nОтправка данных во второй бэкенд...")
        send_violators_to_api(violators)
    else:
        print("Нарушители не обнаружены")


def run_periodically(interval_seconds: int = 10):
    while True:
        try:
            main()
        except Exception as e:
            print(f"Ошибка в main(): {e}")
        print(f"Ждем {interval_seconds} секунд до следующего запуска...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    import os
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

    run_periodically(interval_seconds=10)
