"use client";

import { useState } from "react";
import SearchBar from "@/components/SearchBar";
import CardStack from "@/components/CardStack";

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      <SearchBar onScrapeComplete={() => setRefreshKey((k) => k + 1)} />
      <CardStack key={refreshKey} />
    </div>
  );
}
