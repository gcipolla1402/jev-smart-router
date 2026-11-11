import { FormEvent, useState } from "react";

import { analyzeMessage } from "./api";
import { categories, type AnalyzeResponse, type Category } from "./types";

const examples = [
  { label: "FRAUDE", message: "Meu cartão foi clonado e fizeram uma compra que não reconheço." },
  { label: "SUPORTE", message: "Não consigo acessar minha conta pelo aplicativo." },
  { label: "COMERCIAL", message: "Quero conhecer os planos e preços da empresa." },
  { label: "CANCELAMENTO", message: "Quero cancelar meu serviço." },
];

const categoryLabels: Record<Category, string> = {
  FRAUDE: "FRAUDE",
  SUPORTE_TECNICO: "SUPORTE TÉCNICO",
  COMERCIAL: "COMERCIAL",
  CANCELAMENTO: "CANCELAMENTO",
};

const formatPercent = (value: number) => `${Math.round(value * 100)}%`;
const formatValue = (value: number | null) => (value === null ? "—" : value.toLocaleString("pt-BR"));

export default function App() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim() || loading) return;

    setLoading(true);
    setError("");
    setResult(null);
    setShowDetails(false);

    try {
      setResult(await analyzeMessage(message.trim()));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="eyebrow"><span className="status-dot" /> TYPESAFE JEV</div>
        <h1>JEV SMART ROUTER</h1>
        <p>Mensagem <span>→</span> JEV classifica <span>→</span> Sistema roteia</p>
      </header>

      <section className="card input-card" aria-labelledby="message-label">
        <form onSubmit={handleSubmit}>
          <label id="message-label" htmlFor="message">MENSAGEM DO CLIENTE</label>
          <textarea
            id="message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Digite ou cole a mensagem do cliente"
            rows={6}
            maxLength={10_000}
          />

          <div className="examples" aria-label="Exemplos de mensagens">
            <span>EXEMPLOS</span>
            <div>
              {examples.map((example) => (
                <button key={example.label} type="button" onClick={() => setMessage(example.message)}>
                  {example.label}
                </button>
              ))}
            </div>
          </div>

          <button className="analyze-button" type="submit" disabled={!message.trim() || loading}>
            {loading ? <><span className="spinner" /> ANALISANDO...</> : <>ANALISAR COM JEV <span>→</span></>}
          </button>
        </form>
      </section>

      {error && <div className="error" role="alert">{error}</div>}

      {result && (
        <section className="result" aria-live="polite">
          <div className="result-heading"><span>JEV RESULT</span><i /></div>

          <div className="decision-grid">
            <article className="card decision">
              <span>CATEGORIA</span>
              <strong>{categoryLabels[result.category]}</strong>
            </article>
            <article className="card decision">
              <span>PRIORIDADE</span>
              <strong className={`priority ${result.priority.toLowerCase()}`}>{result.priority}</strong>
            </article>
          </div>

          <article className="card probabilities">
            <span className="section-label">PROBABILIDADES DA CATEGORIA</span>
            <div className="probability-list">
              {[...categories]
                .sort((a, b) => result.probabilities[b] - result.probabilities[a])
                .map((category) => (
                  <div className={category === result.category ? "selected" : ""} key={category}>
                    <span>{categoryLabels[category]}</span>
                    <strong>{formatPercent(result.probabilities[category])}</strong>
                  </div>
                ))}
            </div>
          </article>

          <article className="route-card">
            <span>ROTA DEFINIDA PELO PYTHON</span>
            <strong><b>→</b> {result.queue.replaceAll("_", " ")}</strong>
          </article>

          <button className="details-toggle" type="button" onClick={() => setShowDetails(!showDetails)} aria-expanded={showDetails}>
            {showDetails ? "HIDE TECHNICAL DETAILS" : "SHOW TECHNICAL DETAILS"}
            <span>{showDetails ? "−" : "+"}</span>
          </button>

          {showDetails && (
            <dl className="technical card">
              <div><dt>Modelo</dt><dd>{result.technical_details.model}</dd></div>
              <div><dt>Latência</dt><dd>{result.technical_details.latency_ms} ms</dd></div>
              <div><dt>Input tokens</dt><dd>{formatValue(result.technical_details.input_tokens)}</dd></div>
              <div><dt>Output tokens</dt><dd>{formatValue(result.technical_details.output_tokens)}</dd></div>
              <div><dt>Confidence categoria</dt><dd>{formatPercent(result.technical_details.category_native_confidence)}</dd></div>
              <div><dt>Confidence prioridade</dt><dd>{formatPercent(result.technical_details.priority_native_confidence)}</dd></div>
            </dl>
          )}
        </section>
      )}

      <footer>JEV JULGA <span>•</span> PYTHON ROTEIA</footer>
    </main>
  );
}

