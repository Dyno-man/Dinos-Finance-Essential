import type { Category } from "@/lib/types";

export function CategorySelector({
  categories,
  value,
  name = "category_id",
}: {
  categories: Category[];
  value?: string | null;
  name?: string;
}) {
  return (
    <select name={name} defaultValue={value ?? ""}>
      <option value="">Uncategorized</option>
      {categories.map((category) => (
        <option key={category.id} value={category.id}>
          {category.name}
        </option>
      ))}
    </select>
  );
}
