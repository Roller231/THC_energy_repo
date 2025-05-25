#!/bin/bash

# Ожидание запуска Postgres
echo "Waiting for Postgres..."
sleep 10

# Запуск clients.py
echo "Starting clients.py..."
python clients.py &

sleep 5

# Запуск over.py
echo "Starting over.py..."
python over.py &

sleep 5

# Запуск ML модели
echo "Starting electricity_violation_detector.py..."
python electricity_violation_detector.py

sleep 5

# Запуск бота
echo "Starting bot.py..."
python Bot/bot.py
