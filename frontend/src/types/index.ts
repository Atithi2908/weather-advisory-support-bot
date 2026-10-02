export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface WeatherMetrics {
  temperature?: number;
  wind_speed?: number;
  precipitation?: number;
  precipitation_probability?: number;
  uv_index?: number;
  relative_humidity?: number;
  wind_gusts?: number;
  weather_code?: number;
  time?: string;
  forecast_window?: string;
  is_historical?: boolean;
  units?: Record<string, string>;
}

export interface SOP {
  id: string;
  name: string;
  category: string;
  description: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | string;
  advice: string;
  conditions?: Array<{
    field: string;
    operator: string;
    value: any;
  }>;
}

export interface AdvisoryRecord {
  id: string;
  conversation_id: string;
  user_query: string;
  location?: string;
  activity?: string;
  person_context?: string;
  selected_sop?: SOP;
  matched_sops?: SOP[];
  severity?: string;
  weather_metrics?: WeatherMetrics;
  generated_response?: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  // Attached structured record for assistant messages if available
  advisory_record?: AdvisoryRecord;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: Message[];
  advisory_records?: AdvisoryRecord[];
}

export interface AdvisoryResponse {
  conversation_id: string;
  response?: string;
  message?: string;
  location?: string;
  resolved_location_name?: string;
  activity?: string;
  person_context?: string;
  weather?: WeatherMetrics;
  selected_sop?: SOP;
  matched_sops?: SOP[];
  severity?: string;
}
