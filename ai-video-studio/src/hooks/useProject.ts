import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectApi } from "@/lib/api";
import type { Project } from "@/types";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: projectApi.getAll,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, subject }: { name: string; subject: string }) =>
      projectApi.create(name, subject),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => projectApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}
