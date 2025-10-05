import AuthenticatedLayout from "@/components/layout/AuthenticatedLayout";

export default function Page() {
  return (
    <AuthenticatedLayout>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Hello from Authenticated Layout!
        </h1>
        <p className="text-gray-500 mt-2">
          This is a temporary preview (no authentication required).
        </p>
      </div>
    </AuthenticatedLayout>
  );
}
