export const metadata = {
  title: "Ops Copilot",
  description: "Internal Ops/Support Copilot",
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
