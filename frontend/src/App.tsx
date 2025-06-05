import { useState, useRef } from "react";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import type { Message } from "@/types";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async (input: string, _effort: string, model: string) => {
    if (!input.trim()) return;
    const humanMessage: Message = {
      type: "human",
      content: input,
      id: Date.now().toString(),
    };
    setMessages((prev) => [...prev, humanMessage]);
    setIsLoading(true);
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: input, model }),
    });
    const data = await resp.json();
    const aiMessage: Message = {
      type: "ai",
      content: data.answer,
      id: (Date.now() + 1).toString(),
    };
    setMessages((prev) => [...prev, aiMessage]);
    setIsLoading(false);
  };

  const handleCancel = () => {
    setMessages([]);
  };

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      <main className="flex-1 flex flex-col overflow-hidden max-w-4xl mx-auto w-full">
        <div className={`flex-1 overflow-y-auto ${messages.length === 0 ? "flex" : ""}`}>
          {messages.length === 0 ? (
            <WelcomeScreen handleSubmit={handleSubmit} isLoading={isLoading} onCancel={handleCancel} />
          ) : (
            <ChatMessagesView
              messages={messages}
              isLoading={isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              liveActivityEvents={[]}
              historicalActivities={{}}
            />
          )}
        </div>
      </main>
    </div>
  );
}
