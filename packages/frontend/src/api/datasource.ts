import type { DataSource, DataSourceCreate } from '../types/datasource';

// Load from env, similar to useChat.ts
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

export const DataSourceService = {
    async list(): Promise<DataSource[]> {
        const res = await fetch(`${API_BASE}/datasources`);
        if (!res.ok) throw new Error('Failed to fetch data sources');
        return res.json();
    },

    async create(data: DataSourceCreate): Promise<DataSource> {
        const res = await fetch(`${API_BASE}/datasources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error('Failed to create data source');
        return res.json();
    },

    async delete(id: string): Promise<void> {
        const res = await fetch(`${API_BASE}/datasources/${id}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete data source');
    }
};

