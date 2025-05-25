import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8001'; // Для over_consumers
const API_BASE2 = 'http://127.0.0.1:8000'; // Для clients

const priorityColor = {
  red: 'bg-red-100',
  yellow: 'bg-yellow-100',
  green: 'bg-green-100',
};

const getStatusLabel = (status) => {
  switch (status) {
    case 'no':
      return 'Не проверен';
    case 'under_review':
      return 'На проверке';
    case 'yes':
      return 'Проверено';
    default:
      return status || '—';
  }
};

export default function OverConsumersPage() {
  const [data, setData] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [address, setAddress] = useState('');
  const [searchId, setSearchId] = useState('');
  const [probability, setProbability] = useState(0); // ← начальное значение 0%
  const [loadingIds, setLoadingIds] = useState([]);

  const fetchData = async () => {
    try {
      const consumersRes = await axios.get(`${API_BASE}/over_consumers`);
      const overConsumers = consumersRes.data?.over_consumers;
      setData(Array.isArray(overConsumers) ? overConsumers : []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  const sendToReview = async (accountId) => {
    try {
      setLoadingIds(prev => [...prev, accountId]);
      console.log(`🚀 Отправка клиента ${accountId} на проверку...`);

      const clientPayload = { isChecked: "under_review" };

      await Promise.all([
        axios.patch(`${API_BASE2}/clients/${accountId}`, clientPayload),
        axios.patch(`${API_BASE}/over_consumers/${accountId}`, clientPayload)
      ]);

      console.log(`✅ Успешно обновлены данные клиента ${accountId}`);
      await fetchData();
    } catch (error) {
      console.error(`❌ Ошибка при отправке клиента ${accountId} на проверку:`, error);
    } finally {
      setLoadingIds(prev => prev.filter(id => id !== accountId));
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const threshold = (probability / 100) * 12000;

  const filteredData = data.filter(item => {
    const matchesStatus = !statusFilter ||
      (statusFilter === 'not_checked' && (item.is_checked === 'no' || !item.is_checked)) ||
      (statusFilter === 'under_review' && item.is_checked === 'under_review') ||
      (statusFilter === item.is_checked);

    const matchesAddress = !address || item.address.toLowerCase().includes(address.toLowerCase());
    const matchesId = !searchId || item.account_id.toString().includes(searchId);
    const matchesProbability = item.avg_consumption_6m >= threshold;

    return matchesStatus && matchesAddress && matchesId && matchesProbability;
  });

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <input
          placeholder="Фильтр по ID"
          value={searchId}
          onChange={e => setSearchId(e.target.value)}
          className="border p-2 rounded"
        />

        <input
          placeholder="Фильтр по адресу"
          value={address}
          onChange={e => setAddress(e.target.value)}
          className="border p-2 rounded"
        />

        <select 
          value={statusFilter} 
          onChange={e => setStatusFilter(e.target.value)}
          className="border p-2 rounded"
        >
          <option value="">Все статусы</option>
          <option value="not_checked">Не проверен</option>
          <option value="under_review">На проверке</option>
        </select>

        <div className="col-span-2 flex items-center space-x-2">
          <span>Вероятность: {probability}%</span>
          <input
            type="range"
            min="0"
            max="100"
            value={probability}
            onChange={e => setProbability(+e.target.value)}
            className="flex-1"
          />
        </div>
      </div>

      <div className="grid gap-4">
        {filteredData.map(client => (
          <div key={client.account_id} className={`p-4 border rounded ${priorityColor[client.priority] || ''}`}>
            <p><strong>ID:</strong> {client.account_id}</p>
            <p><strong>Адрес:</strong> {client.address}</p>
            <p><strong>Потребление:</strong> {client.avg_consumption_6m} кВт·ч</p>
            <p><strong>Статус:</strong> {getStatusLabel(client.is_checked)}</p>

            {client.is_checked !== 'under_review' && (
              <button
                onClick={() => sendToReview(client.account_id)}
                disabled={loadingIds.includes(client.account_id)}
                className={`mt-2 px-4 py-2 rounded ${
                  loadingIds.includes(client.account_id)
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                {loadingIds.includes(client.account_id) ? 'Отправка...' : 'Отправить на проверку'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
