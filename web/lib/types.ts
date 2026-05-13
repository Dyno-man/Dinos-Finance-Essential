export type AuthUser = {
  id: string;
  username: string;
  email: string | null;
  role: string;
  plan: string;
};

export type Category = {
  id: string;
  name: string;
  color: string | null;
  is_default: boolean;
};

export type ReceiptStatus = "processing" | "pending_review" | "confirmed" | "failed";

export type Receipt = {
  id: string;
  source: string;
  merchant_name: string | null;
  purchased_at: string | null;
  amount_cents: number | null;
  currency: string;
  category_id: string | null;
  category: Category | null;
  status: ReceiptStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type ReceiptImage = {
  id: string;
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  created_at: string;
  url: string;
};

export type OCRResult = {
  id: string;
  raw_text: string;
  parsed_total_cents: number | null;
  parsed_merchant: string | null;
  parser_version: string;
  confidence: number | null;
  created_at: string;
};

export type ReceiptDetail = {
  receipt: Receipt;
  images: ReceiptImage[];
  ocr_result: OCRResult | null;
};

export type ReceiptListResponse = {
  receipts: Receipt[];
  total: number;
  limit: number;
  offset: number;
};

export type AnalyticsSummary = {
  total_cents: number;
  confirmed_receipt_count: number;
  receipt_count: number;
  average_receipt_cents: number;
  pending_review_count: number;
  monthly_spend: { month: string; amount_cents: number }[];
  category_spend: { category_id: string | null; name: string; amount_cents: number; color: string | null }[];
  merchant_spend: { merchant_name: string; amount_cents: number }[];
  source_counts: { source: string; count: number }[];
};

export type Integration = {
  id: string;
  provider: string;
  status: string;
  display_name: string | null;
  created_at: string;
};

export type BillingSummary = {
  plan_name: string;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};
