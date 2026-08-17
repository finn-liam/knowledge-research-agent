import { BarChart3, Layers, Settings } from "lucide-react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { HomePage } from "@/pages/home/HomePage";
import { KnowledgeBasePage } from "@/pages/knowledge-base/KnowledgeBasePage";
import { LibraryPage } from "@/pages/library/LibraryPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
import { ResearchPage } from "@/pages/research/ResearchPage";

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/research/:taskId", element: <ResearchPage /> },
      { path: "/library", element: <LibraryPage /> },
      { path: "/knowledge-base", element: <KnowledgeBasePage /> },
      { path: "/datasources", element: <PlaceholderPage title="Datasources" icon={Layers} /> },
      { path: "/analytics", element: <PlaceholderPage title="Analytics" icon={BarChart3} /> },
      { path: "/settings", element: <PlaceholderPage title="Settings" icon={Settings} /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
