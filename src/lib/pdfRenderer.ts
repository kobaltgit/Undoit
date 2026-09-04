import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

if (typeof window !== 'undefined' && pdfjsLib.GlobalWorkerOptions) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;
}

export interface RenderResult {
  dataUrl: string;
  totalPages: number;
}

export function isVisualDocument(filename: string | undefined): boolean {
  if (!filename) return false;
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg', 'bmp', 'ico', 'avif', 'tiff', 'tif', 'pdf', 'ai', 'psd'].includes(ext);
}

export function isPdfOrAi(filename: string | undefined): boolean {
  if (!filename) return false;
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return ['pdf', 'ai'].includes(ext);
}

export function isDocx(filename: string | undefined): boolean {
  if (!filename) return false;
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return ext === 'docx';
}

/**
 * Extracts embedded XMP raster thumbnail (e.g. from Adobe Illustrator or Photoshop files)
 */
export function extractXmpThumbnail(bytes: Uint8Array): string | null {
  try {
    const searchLimit = Math.min(bytes.length, 3 * 1024 * 1024);
    let text = '';
    const slice = bytes.subarray(0, searchLimit);
    for (let i = 0; i < slice.length; i++) {
      text += String.fromCharCode(slice[i]);
    }

    const match = text.match(/<x[am]pGImg:image>([\s\S]*?)<\/x[am]pGImg:image>/i);
    if (match && match[1]) {
      const cleanB64 = match[1].replace(/\s+/g, '');
      if (cleanB64.length > 50) {
        return `data:image/jpeg;base64,${cleanB64}`;
      }
    }
  } catch (e) {
    console.warn('Failed to extract XMP thumbnail:', e);
  }
  return null;
}

/**
 * Renders a PDF or AI document page into a base64 PNG data URL
 */
export async function renderPdfToDataUrl(
  bytes: Uint8Array,
  pageNumber: number = 1,
  scale: number = 1.5
): Promise<RenderResult> {
  try {
    const dataCopy = new Uint8Array(bytes);
    const loadingTask = pdfjsLib.getDocument({
      data: dataCopy,
      cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/cmaps/',
      cMapPacked: true,
    });

    const pdfDoc = await loadingTask.promise;
    const totalPages = pdfDoc.numPages;
    const pageNumClamped = Math.max(1, Math.min(pageNumber, totalPages));
    const page = await pdfDoc.getPage(pageNumClamped);

    const viewport = page.getViewport({ scale });
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Canvas 2D context not available');
    }

    canvas.width = viewport.width;
    canvas.height = viewport.height;

    // Fill white background for pages that have transparent background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    await page.render({
      canvasContext: ctx,
      viewport: viewport,
    }).promise;

    const dataUrl = canvas.toDataURL('image/png');
    return { dataUrl, totalPages };
  } catch (err) {
    // If standard PDF parsing fails (e.g. AI file saved without PDF compatibility), fallback to XMP thumbnail
    const xmpThumb = extractXmpThumbnail(bytes);
    if (xmpThumb) {
      return { dataUrl: xmpThumb, totalPages: 1 };
    }
    throw err;
  }
}
