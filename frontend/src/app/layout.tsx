import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Support Request Form',
  description: 'Submit a support request to our team',
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
