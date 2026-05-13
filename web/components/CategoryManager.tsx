"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { jsonApi } from "@/lib/client-api";
import type { Category } from "@/lib/types";

export function CategoryManager({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const [error, setError] = useState("");

  async function createCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    setError("");
    try {
      await jsonApi("/categories", {
        method: "POST",
        body: JSON.stringify({ name: formData.get("name"), color: formData.get("color") || null }),
      });
      form.reset();
      router.refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not create category");
    }
  }

  async function updateCategory(event: FormEvent<HTMLFormElement>, categoryId: string) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    setError("");
    try {
      await jsonApi(`/categories/${categoryId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: formData.get("name"), color: formData.get("color") || null }),
      });
      router.refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not update category");
    }
  }

  return (
    <section className="panel-section">
      <div className="section-heading">
        <h2>Categories</h2>
      </div>
      <div className="category-list">
        {categories.map((category) => (
          <span className="category-pill" key={category.id}>
            <span style={{ background: category.color ?? "#667085" }} />
            {category.name}
          </span>
        ))}
      </div>
      <div className="category-edit-list">
        {categories
          .filter((category) => !category.is_default)
          .map((category) => (
            <form className="inline-form" key={category.id} onSubmit={(event) => void updateCategory(event, category.id)}>
              <label>
                Name
                <input name="name" required maxLength={80} defaultValue={category.name} />
              </label>
              <label>
                Color
                <input name="color" maxLength={32} defaultValue={category.color ?? ""} />
              </label>
              <button type="submit">Save</button>
            </form>
          ))}
      </div>
      <form className="inline-form" onSubmit={(event) => void createCategory(event)}>
        <label>
          Category name
          <input name="name" required maxLength={80} />
        </label>
        <label>
          Color
          <input name="color" placeholder="#0f766e" maxLength={32} />
        </label>
        <button type="submit">Add category</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
