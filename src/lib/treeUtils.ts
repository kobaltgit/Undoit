export interface TrackedFile {
  id: number;
  original_path: string;
  filename: string;
  folder_id: number | null;
  is_active: boolean;
  updated_at: string;
  version_count: number;
  latest_size: number;
}

export interface WatchedFolder {
  id: number;
  path: string;
  created_at: string;
}

export interface TreeNode {
  id: string; // Unique id (e.g. folder full path or file id)
  name: string;
  path: string;
  type: "folder" | "file";
  file?: TrackedFile;
  children: TreeNode[];
  fileCount: number;
  versionCount: number;
  depth: number;
  isWatchedRoot?: boolean;
}

export function normalizePath(p: string): string {
  return p.replace(/\\/g, "/").replace(/\/+$/, "");
}

export function getBaseName(p: string): string {
  const norm = normalizePath(p);
  const idx = norm.lastIndexOf("/");
  return idx !== -1 ? norm.slice(idx + 1) : norm;
}

/**
 * Builds a hierarchical tree from tracked files and watched folders.
 */
export function buildFileTree(
  files: TrackedFile[],
  watchedFolders: WatchedFolder[],
  otherFilesLabel = "Другие файлы"
): TreeNode[] {
  const roots: TreeNode[] = [];
  const filesAssigned = new Set<number>();

  // Normalize watched folder paths
  const normFolders = watchedFolders.map((f) => ({
    ...f,
    normPath: normalizePath(f.path),
    lowerPath: normalizePath(f.path).toLowerCase(),
  }));

  // Sort watched folders by path length descending (so more specific nested folders match first if any)
  normFolders.sort((a, b) => b.normPath.length - a.normPath.length);

  // 1. Build tree for each watched folder
  for (const folder of normFolders) {
    const rootNode: TreeNode = {
      id: `folder:${folder.normPath}`,
      name: getBaseName(folder.normPath) || folder.normPath,
      path: folder.normPath,
      type: "folder",
      children: [],
      fileCount: 0,
      versionCount: 0,
      depth: 0,
      isWatchedRoot: true,
    };

    // Find all files belonging to this watched folder
    for (const file of files) {
      if (filesAssigned.has(file.id)) continue;
      const normFilePath = normalizePath(file.original_path);
      const lowerFilePath = normFilePath.toLowerCase();

      if (
        lowerFilePath === folder.lowerPath ||
        lowerFilePath.startsWith(folder.lowerPath + "/")
      ) {
        filesAssigned.add(file.id);
        const relPath = normFilePath.slice(folder.normPath.length).replace(/^\/+/, "");
        addFileToSubtree(rootNode, file, relPath, folder.normPath, 1);
      }
    }

    calculateCountsAndSort(rootNode);
    roots.push(rootNode);
  }

  // 2. Any leftover files that don't belong to current watched folders
  const unassignedFiles = files.filter((f) => !filesAssigned.has(f.id));
  if (unassignedFiles.length > 0) {
    const otherRoot: TreeNode = {
      id: "folder:__other__",
      name: otherFilesLabel,
      path: "__other__",
      type: "folder",
      children: [],
      fileCount: 0,
      versionCount: 0,
      depth: 0,
      isWatchedRoot: true,
    };

    for (const file of unassignedFiles) {
      const normFilePath = normalizePath(file.original_path);
      // Group by directory of the file
      const dirIdx = normFilePath.lastIndexOf("/");
      const dirPath = dirIdx !== -1 ? normFilePath.slice(0, dirIdx) : "";
      const dirName = dirPath ? getBaseName(dirPath) : "";

      if (dirName) {
        let dirNode = otherRoot.children.find(
          (c) => c.type === "folder" && c.path === dirPath
        );
        if (!dirNode) {
          dirNode = {
            id: `folder:${dirPath}`,
            name: dirName,
            path: dirPath,
            type: "folder",
            children: [],
            fileCount: 0,
            versionCount: 0,
            depth: 1,
          };
          otherRoot.children.push(dirNode);
        }
        dirNode.children.push({
          id: `file:${file.id}`,
          name: file.filename,
          path: normFilePath,
          type: "file",
          file,
          children: [],
          fileCount: 1,
          versionCount: file.version_count,
          depth: 2,
        });
      } else {
        otherRoot.children.push({
          id: `file:${file.id}`,
          name: file.filename,
          path: normFilePath,
          type: "file",
          file,
          children: [],
          fileCount: 1,
          versionCount: file.version_count,
          depth: 1,
        });
      }
    }

    calculateCountsAndSort(otherRoot);
    roots.push(otherRoot);
  }

  return roots;
}

function addFileToSubtree(
  parentNode: TreeNode,
  file: TrackedFile,
  relPath: string,
  parentFullPath: string,
  depth: number
) {
  const parts = relPath.split("/").filter(Boolean);

  if (parts.length === 0) {
    return;
  }

  if (parts.length === 1) {
    // Direct child file
    parentNode.children.push({
      id: `file:${file.id}`,
      name: parts[0],
      path: normalizePath(file.original_path),
      type: "file",
      file,
      children: [],
      fileCount: 1,
      versionCount: file.version_count,
      depth,
    });
    return;
  }

  // Nested directory
  const segment = parts[0];
  const currentSubPath = `${parentFullPath}/${segment}`;

  let subFolder = parentNode.children.find(
    (c) => c.type === "folder" && c.name.toLowerCase() === segment.toLowerCase()
  );

  if (!subFolder) {
    subFolder = {
      id: `folder:${currentSubPath}`,
      name: segment,
      path: currentSubPath,
      type: "folder",
      children: [],
      fileCount: 0,
      versionCount: 0,
      depth,
    };
    parentNode.children.push(subFolder);
  }

  const remainingRelPath = parts.slice(1).join("/");
  addFileToSubtree(subFolder, file, remainingRelPath, currentSubPath, depth + 1);
}

function calculateCountsAndSort(node: TreeNode) {
  let totalFiles = 0;
  let totalVersions = 0;

  for (const child of node.children) {
    if (child.type === "folder") {
      calculateCountsAndSort(child);
      totalFiles += child.fileCount;
      totalVersions += child.versionCount;
    } else {
      totalFiles += 1;
      totalVersions += child.versionCount;
    }
  }

  node.fileCount = totalFiles;
  node.versionCount = totalVersions;

  // Sort: folders first, then files, alphabetically case-insensitive
  node.children.sort((a, b) => {
    if (a.type !== b.type) {
      return a.type === "folder" ? -1 : 1;
    }
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base", numeric: true });
  });
}

export interface FilterResult {
  nodes: TreeNode[];
  autoExpandIds: Set<string>;
}

/**
 * Filters tree by search query and collects parent folder IDs that should be expanded.
 */
export function filterTree(nodes: TreeNode[], query: string): FilterResult {
  const cleanQuery = query.trim().toLowerCase();
  const autoExpandIds = new Set<string>();

  if (!cleanQuery) {
    return { nodes, autoExpandIds };
  }

  function filterNode(node: TreeNode): TreeNode | null {
    if (node.type === "file") {
      const match =
        node.name.toLowerCase().includes(cleanQuery) ||
        node.path.toLowerCase().includes(cleanQuery);
      return match ? { ...node } : null;
    }

    // Folder
    const filteredChildren: TreeNode[] = [];
    for (const child of node.children) {
      const filteredChild = filterNode(child);
      if (filteredChild) {
        filteredChildren.push(filteredChild);
      }
    }

    if (filteredChildren.length > 0) {
      autoExpandIds.add(node.id);
      let fCount = 0;
      let vCount = 0;
      for (const c of filteredChildren) {
        fCount += c.fileCount;
        vCount += c.versionCount;
      }
      return {
        ...node,
        children: filteredChildren,
        fileCount: fCount,
        versionCount: vCount,
      };
    }

    return null;
  }

  const filteredNodes: TreeNode[] = [];
  for (const root of nodes) {
    const res = filterNode(root);
    if (res) {
      filteredNodes.push(res);
    }
  }

  return { nodes: filteredNodes, autoExpandIds };
}

/**
 * Returns all folder IDs in a tree
 */
export function getAllFolderIds(nodes: TreeNode[]): string[] {
  const ids: string[] = [];
  function traverse(list: TreeNode[]) {
    for (const n of list) {
      if (n.type === "folder") {
        ids.push(n.id);
        traverse(n.children);
      }
    }
  }
  traverse(nodes);
  return ids;
}
