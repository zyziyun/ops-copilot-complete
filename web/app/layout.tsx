import "./globals.css";

export const metadata = {
  title: "Ops Copilot",
  description: "Internal Ops/Support Copilot — streaming agent client",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
