"use client";

import { Tab, TabGroup, TabList, TabPanel, TabPanels } from "@tremor/react";
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

      <TabGroup>
        <div className="sticky top-0 z-10 bg-gray-950/90 px-4 pb-2 backdrop-blur">
          <TabList variant="solid" className="w-full">
            <Tab className="flex-1 justify-center">Overview</Tab>
            <Tab className="flex-1 justify-center">Recovery</Tab>
            <Tab className="flex-1 justify-center">Body</Tab>
            <Tab className="flex-1 justify-center">Training</Tab>
          </TabList>
        </div>

        <TabPanels className="px-4 pt-3">
          <TabPanel>
            <Overview />
          </TabPanel>
          <TabPanel>
            <Recovery />
          </TabPanel>
          <TabPanel>
            <Body />
          </TabPanel>
          <TabPanel>
            <Training />
          </TabPanel>
        </TabPanels>
      </TabGroup>

      <p className="mt-6 px-5 text-center text-tremor-label text-gray-600">
        Apple Health · Hevy · Strava · updated {dashboard.last_data_date}
      </p>
    </main>
  );
}
