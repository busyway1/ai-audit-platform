"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2Icon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/app/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";
import { Input } from "@/app/components/ui/input";
import { Button } from "@/app/components/ui/button";
import { useProjectStore } from "@/app/stores/useProjectStore";
import type { AuditProjectStatus } from "@/app/types/supabase";

const PROJECT_STATUSES: { value: AuditProjectStatus; label: string }[] = [
  { value: "Planning", label: "Planning" },
  { value: "Execution", label: "Execution" },
  { value: "Review", label: "Review" },
  { value: "Completed", label: "Completed" },
];

const currentYear = new Date().getFullYear();

const projectFormSchema = z.object({
  client_name: z
    .string()
    .min(1, "Client name is required")
    .max(100, "Client name must be less than 100 characters"),
  fiscal_year: z
    .number({
      required_error: "Fiscal year is required",
      invalid_type_error: "Fiscal year must be a number",
    })
    .int("Fiscal year must be a whole number")
    .min(2000, "Fiscal year must be 2000 or later")
    .max(2100, "Fiscal year must be 2100 or earlier"),
  overall_materiality: z
    .number({
      invalid_type_error: "Materiality must be a number",
    })
    .positive("Materiality must be a positive number")
    .nullable()
    .optional(),
  status: z.enum(["Planning", "Execution", "Review", "Completed"], {
    required_error: "Status is required",
  }),
});

type ProjectFormValues = z.infer<typeof projectFormSchema>;

interface ProjectRegistrationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ProjectRegistrationModal({
  open,
  onOpenChange,
  onSuccess,
}: ProjectRegistrationModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const createProject = useProjectStore((state) => state.createProject);
  const selectProject = useProjectStore((state) => state.selectProject);

  const form = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      client_name: "",
      fiscal_year: currentYear,
      overall_materiality: null,
      status: "Planning",
    },
  });

  const handleSubmit = async (values: ProjectFormValues) => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const newProject = await createProject({
        client_name: values.client_name,
        fiscal_year: values.fiscal_year,
        overall_materiality: values.overall_materiality ?? null,
        status: values.status,
      });

      if (newProject) {
        selectProject(newProject.id);
        form.reset();
        onOpenChange(false);
        onSuccess?.();
      } else {
        setSubmitError("Failed to create project. Please try again.");
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An unexpected error occurred";
      setSubmitError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      form.reset();
      setSubmitError(null);
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogDescription>
            Enter the details for the new audit project. Click save when you're
            done.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            className="space-y-4"
          >
            <FormField
              control={form.control}
              name="client_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Client Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter client name"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="fiscal_year"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Fiscal Year</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      placeholder="Enter fiscal year"
                      {...field}
                      onChange={(e) => {
                        const value = e.target.value;
                        field.onChange(value === "" ? undefined : Number(value));
                      }}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormDescription>
                    The fiscal year end for the audit engagement
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="overall_materiality"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Overall Materiality (Optional)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      placeholder="Enter materiality amount"
                      value={field.value ?? ""}
                      onChange={(e) => {
                        const value = e.target.value;
                        field.onChange(value === "" ? null : Number(value));
                      }}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormDescription>
                    The overall materiality threshold for the audit
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                    disabled={isSubmitting}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select project status" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {PROJECT_STATUSES.map((status) => (
                        <SelectItem key={status.value} value={status.value}>
                          {status.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    The current phase of the audit project
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {submitError && (
              <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                {submitError}
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && (
                  <Loader2Icon className="size-4 animate-spin" />
                )}
                {isSubmitting ? "Creating..." : "Create Project"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
