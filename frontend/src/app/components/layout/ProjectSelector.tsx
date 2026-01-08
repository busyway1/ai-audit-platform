"use client";

import { useEffect } from "react";
import { ChevronDownIcon, FolderIcon, CheckIcon, PlusIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import { Button } from "@/app/components/ui/button";
import { useProjectStore, getSelectedProject } from "@/app/stores/useProjectStore";
import { cn } from "@/app/components/ui/utils";
import type { AuditProjectStatus } from "@/app/types/supabase";

interface ProjectSelectorProps {
  onNewProject?: () => void;
  className?: string;
}

const STATUS_COLORS: Record<AuditProjectStatus, string> = {
  Planning: "bg-yellow-100 text-yellow-800",
  Execution: "bg-blue-100 text-blue-800",
  Review: "bg-purple-100 text-purple-800",
  Completed: "bg-green-100 text-green-800",
};

export function ProjectSelector({ onNewProject, className }: ProjectSelectorProps) {
  const projects = useProjectStore((state) => state.projects);
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const loading = useProjectStore((state) => state.loading);
  const error = useProjectStore((state) => state.error);
  const fetchProjects = useProjectStore((state) => state.fetchProjects);
  const selectProject = useProjectStore((state) => state.selectProject);
  const subscribeToUpdates = useProjectStore((state) => state.subscribeToUpdates);

  const selectedProject = useProjectStore(getSelectedProject);
  const projectList = Object.values(projects);

  useEffect(() => {
    fetchProjects();
    const unsubscribe = subscribeToUpdates();
    return () => unsubscribe();
  }, [fetchProjects, subscribeToUpdates]);

  const handleProjectSelect = (projectId: string) => {
    selectProject(projectId);
  };

  const formatFiscalYear = (year: number): string => {
    return `FY${year}`;
  };

  const renderTriggerContent = () => {
    if (loading) {
      return (
        <span className="text-muted-foreground">Loading projects...</span>
      );
    }

    if (error) {
      return (
        <span className="text-destructive">Error loading projects</span>
      );
    }

    if (!selectedProject) {
      return (
        <span className="text-muted-foreground">Select a project</span>
      );
    }

    return (
      <div className="flex items-center gap-2">
        <FolderIcon className="size-4 text-blue-600" />
        <span className="font-medium truncate max-w-[150px]">
          {selectedProject.client_name}
        </span>
        <span className="text-muted-foreground text-xs">
          {formatFiscalYear(selectedProject.fiscal_year)}
        </span>
      </div>
    );
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "min-w-[200px] justify-between gap-2",
            className
          )}
          disabled={loading}
        >
          {renderTriggerContent()}
          <ChevronDownIcon className="size-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-[280px]">
        <DropdownMenuLabel>Audit Projects</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {projectList.length === 0 && !loading && (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            <FolderIcon className="size-8 mx-auto mb-2 opacity-50" />
            <p>No projects found</p>
            <p className="text-xs mt-1">Create a new project to get started</p>
          </div>
        )}

        {projectList.length > 0 && (
          <DropdownMenuGroup>
            {projectList.map((project) => {
              const isSelected = project.id === selectedProjectId;

              return (
                <DropdownMenuItem
                  key={project.id}
                  onSelect={() => handleProjectSelect(project.id)}
                  className="flex items-center justify-between gap-2 cursor-pointer"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <FolderIcon
                      className={cn(
                        "size-4 shrink-0",
                        isSelected ? "text-blue-600" : "text-muted-foreground"
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate">
                        {project.client_name}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatFiscalYear(project.fiscal_year)}</span>
                        <span
                          className={cn(
                            "px-1.5 py-0.5 rounded text-[10px] font-medium",
                            STATUS_COLORS[project.status]
                          )}
                        >
                          {project.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  {isSelected && (
                    <CheckIcon className="size-4 text-blue-600 shrink-0" />
                  )}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuGroup>
        )}

        {onNewProject && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={onNewProject}
              className="cursor-pointer text-blue-600 focus:text-blue-600"
            >
              <PlusIcon className="size-4" />
              <span>New Project</span>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
