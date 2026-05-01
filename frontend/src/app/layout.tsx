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
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      </head>
      <body style={{ margin: 0, padding: 0, overflowX: 'hidden', width: '100%' }}>{children}</body>
    </html>
  );
}
