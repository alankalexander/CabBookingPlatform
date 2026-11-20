import "./globals.css";
import "leaflet/dist/leaflet.css";
import Toaster from "../components/Toaster";

export const metadata = { title: "CabGo" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-2 focus:bg-white">Skip to content</a>
        <header className="bg-black text-white p-4 flex flex-wrap gap-x-6 gap-y-1">
          <b>🚖 CabGo</b>
          <a href="/">Rider</a>
          <a href="/driver">Driver</a>
        </header>
        <main id="main" className="max-w-4xl mx-auto p-3 sm:p-4">{children}</main>
        <Toaster />
      </body>
    </html>
  );
}