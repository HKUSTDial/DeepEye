export interface DataSource {
    id: string;
    name: string;
    type: string;
    connection_string: string;
    created_at: string;
}

export interface DataSourceCreate {
    name: string;
    type: string;
    connection_string: string;
}

