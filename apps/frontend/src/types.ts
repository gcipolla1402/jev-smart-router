export const categories = [
  "FRAUDE",
  "SUPORTE_TECNICO",
  "COMERCIAL",
  "CANCELAMENTO",
] as const;

export type Category = (typeof categories)[number];
export type Priority = "BAIXA" | "MEDIA" | "ALTA";

export interface TechnicalDetails {
  model: string;
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  category_native_confidence: number;
  priority_native_confidence: number;
}

export interface AnalyzeResponse {
  category: Category;
  priority: Priority;
  probabilities: Record<Category, number>;
  queue: string;
  technical_details: TechnicalDetails;
}

