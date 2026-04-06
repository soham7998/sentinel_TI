import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useState } from "react";

export default function Portfolio() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">

      {/* Background */}
      <div className="absolute inset-0 z-0 bg-[radial-gradient(circle,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-[size:40px_40px]" />

      {/* Flow Lines */}
      <div className="absolute inset-0 z-0">
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            animate={{ x: [0, 400, -200, 0], opacity: [0.2, 0.7, 0.2] }}
            transition={{ duration: 10 + i * 2, repeat: Infinity }}
            className="absolute w-[500px] h-[2px] bg-white/20 blur-sm"
          />
        ))}
      </div>

      {/* HERO */}
      <section className="relative z-10 flex flex-col items-center justify-center h-screen text-center px-4">
        <h1 className="text-6xl font-bold mb-4">🛡️ SentinelTI</h1>
        <p className="text-gray-400 max-w-2xl">
          Explainable Threat Intelligence Dashboard using ML + SHAP
        </p>
        <div className="flex gap-4 mt-6">
          <Button>Live Dashboard</Button>
          <a href="https://github.com/soham7998/sentinel_TI" target="_blank">
            <Button variant="outline">GitHub</Button>
          </a>
        </div>
      </section>

      {/* Tabs */}
      <div className="relative z-10 flex justify-center gap-6 border-b border-white/10 pb-4">
        {["overview", "architecture", "ml-model", "repo", "contact"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`capitalize ${activeTab === tab ? "text-white" : "text-gray-500"}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* CONTENT */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-16">

        {/* OVERVIEW */}
        {activeTab === "overview" && (
          <div>
            <h2 className="text-3xl mb-6">Overview</h2>
            <p className="text-gray-400">
              Real-time IP threat detection with explainable ML scoring.
            </p>
          </div>
        )}

        {/* ARCHITECTURE */}
        {activeTab === "architecture" && (
          <div>
            <h2 className="text-3xl mb-6">Architecture</h2>
            <div className="space-y-3">
              {["Feeds → Ingestion", "Enrichment APIs", "MongoDB", "ML Engine", "SHAP", "Dashboard"].map((step, i) => (
                <div key={i} className="bg-white/5 p-3 rounded">{step}</div>
              ))}
            </div>
          </div>
        )}

        {/* ML MODEL */}
        {activeTab === "ml-model" && (
          <div>
            <h2 className="text-3xl mb-6">ML Model</h2>
            <p className="text-gray-400">Random Forest + XGBoost + Logistic Regression (Stacking)</p>
          </div>
        )}

        {/* REPO VIEWER (NEW 🔥) */}
        {activeTab === "repo" && (
          <div>
            <h2 className="text-3xl mb-6">Repository Explorer</h2>

            <div className="bg-white/5 p-6 rounded-xl font-mono text-sm">
              <p>📁 sentinel_TI/</p>
              <p className="ml-4">📁 backend/</p>
              <p className="ml-8">📄 main.py</p>
              <p className="ml-8">📄 feeds.py</p>
              <p className="ml-8">📄 ml_model.py</p>
              <p className="ml-4">📁 frontend/</p>
              <p className="ml-8">📄 app.py</p>
              <p className="ml-4">📄 docker-compose.yml</p>
              <p className="ml-4">📄 README.md</p>
            </div>

            <div className="mt-6">
              <a href="https://github.com/soham7998/sentinel_TI" target="_blank">
                <Button>Open Full Repo</Button>
              </a>
            </div>
          </div>
        )}

        {/* CONTACT */}
        {activeTab === "contact" && (
          <div className="text-center">
            <h2 className="text-3xl mb-6">Contact</h2>
            <a href="https://www.linkedin.com/in/YOUR-LINKEDIN" className="text-blue-400 underline">
              LinkedIn Profile
            </a>
          </div>
        )}
      </div>

      <footer className="text-center py-6 text-gray-500 text-sm">
        © 2026 SentinelTI
      </footer>
    </div>
  );
}
