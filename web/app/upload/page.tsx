import { AppShell } from "@/components/AppShell";
import { ReceiptUploadDropzone } from "@/components/ReceiptUploadDropzone";
import { requireUser } from "@/lib/server-api";

export default async function UploadPage() {
  const user = await requireUser();
  return (
    <AppShell user={user} title="Upload receipt">
      <section className="panel-section upload-page">
        <ReceiptUploadDropzone />
      </section>
    </AppShell>
  );
}
