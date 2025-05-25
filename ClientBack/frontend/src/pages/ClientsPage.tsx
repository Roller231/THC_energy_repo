import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

interface Client {
  account_id: number;
  is_commercial: boolean;
  address: string;
  building_type: string;
  rooms_count: number;
  residents_count: number;
  total_area: number;
  consumption: {
    [key: string]: number;
  };
  is_checked?: string;
}

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [filteredClients, setFilteredClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchId, setSearchId] = useState('');
  const [searchAddress, setSearchAddress] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchClients = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/clients/get`);
      const list = res.data?.clients;
      const clientsList = Array.isArray(list) ? list : [];
      setClients(clientsList);
      setFilteredClients(clientsList);
    } catch (error) {
      console.error('Failed to fetch clients:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  useEffect(() => {
    const filtered = clients.filter(client => {
      const matchesId = !searchId || client.account_id.toString().includes(searchId);
      const matchesAddress = !searchAddress || client.address.toLowerCase().includes(searchAddress.toLowerCase());
      const matchesStatus =
        !statusFilter ||
        (statusFilter === 'not_checked' && (!client.is_checked || client.is_checked === 'no')) ||
        client.is_checked === statusFilter;
      return matchesId && matchesAddress && matchesStatus;
    });
    setFilteredClients(filtered);
  }, [searchId, searchAddress, statusFilter, clients]);

  const getStatusLabel = (status?: string) => {
    switch (status) {
      case 'no':
        return 'Не проверен';
      case 'under_review':
        return 'На проверке';

      default:
        return '—';
    }
  };

  const calculateAvgConsumption = (consumption: { [key: string]: number }) => {
    const values = Object.values(consumption);
    return values.length > 0
      ? (values.reduce((sum, val) => sum + val, 0) / values.length).toFixed(2)
      : '—';
  };

  if (loading) {
    return <div className="p-4">Загрузка данных...</div>;
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Список клиентов</h1>

      <div className="mb-4 flex flex-col md:flex-row gap-2">
        <input
          type="text"
          placeholder="Поиск по ID клиента"
          value={searchId}
          onChange={(e) => setSearchId(e.target.value)}
          className="border p-2 rounded w-full md:w-64"
        />
        <input
          type="text"
          placeholder="Поиск по адресу"
          value={searchAddress}
          onChange={(e) => setSearchAddress(e.target.value)}
          className="border p-2 rounded w-full md:w-64"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border p-2 rounded w-full md:w-64"
        >
          <option value="">Все статусы</option>
          <option value="not_checked">Не проверен</option>
          <option value="under_review">На проверке</option>

        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full border">
          <thead>
            <tr className="bg-gray-100">
              <th className="border p-2">ID</th>
              <th className="border p-2">Тип</th>
              <th className="border p-2">Адрес</th>
              <th className="border p-2">Тип здания</th>
              <th className="border p-2">Комнат</th>
              <th className="border p-2">Жильцов</th>
              <th className="border p-2">Площадь</th>
              <th className="border p-2">Ср. потребление</th>
              <th className="border p-2">Статус проверки</th>
            </tr>
          </thead>
          <tbody>
            {filteredClients.map(client => (
              <tr key={client.account_id} className="hover:bg-gray-50">
                <td className="border p-2">{client.account_id}</td>
                <td className="border p-2">{client.is_commercial ? 'Коммерческий' : 'Частный'}</td>
                <td className="border p-2">{client.address}</td>
                <td className="border p-2">{client.building_type}</td>
                <td className="border p-2">{client.rooms_count}</td>
                <td className="border p-2">{client.residents_count}</td>
                <td className="border p-2">{client.total_area} м²</td>
                <td className="border p-2">{calculateAvgConsumption(client.consumption)} кВт·ч</td>
                <td className="border p-2">{getStatusLabel(client.is_checked)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
