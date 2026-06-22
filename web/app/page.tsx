"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Header } from "@/components/Header";
import { Overview } from "@/components/tabs/Overview";
import { Recovery } from "@/components/tabs/Recovery";
import { Body } from "@/components/tabs/Body";
import { Training } from "@/components/tabs/Training";
import { dashboard } from "@/lib/data";

export default function Page() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-md pb-10">
      <Header />

      <Tabs defaultValue="overview">
        <div className="sticky top-0 z-10 bg-gray-950/90 px-4 pb-2 backdrop-blur">
          <TabsList className="w-full">
            <TabsTrigger value="overview" className="flex-1">Overview</TabsTrigger>
            <TabsTrigger value="recovery" className="flex-1">Recovery</TabsTrigger>
            <TabsTrigger value="body" className="flex-1">Body</TabsTrigger>
            <TabsTrigger value="training" className="flex-1">Training</TabsTrigger>
          </TabsList>
        </div>
        <div className="px-4 pt-3">
          <TabsContent value="overview"><Overview /></TabsContent>
          <TabsContent value="recovery"><Recovery /></TabsContent>
          <TabsContent value="body"><Body /></TabsContent>
          <TabsContent value="training"><Training /></TabsContent>
        </div>
      </Tabs>

      <p className="mt-6 px-5 text-center text-xs text-gray-600">
        Apple Health · Hevy · Strava · updated {dashboard.last_data_date}
      </p>
    </main>
  );
}
