import CompanyPage from './CompanyPage';

export default async function Company({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  return <CompanyPage ticker={ticker} />;
}
