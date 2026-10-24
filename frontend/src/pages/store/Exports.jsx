import { useState } from 'react';
import { exportPdfApi, exportCsvUrl } from '../../api/storeApi';
import { API_BASE_URL, getAccessToken } from '../../api/axiosClient';
import { FileDown, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

export const Exports = () => {
  const [sections, setSections] = useState({ summary: true, top_rules: true, top_products: true });
  const [generating, setGenerating] = useState(false);

  const toggle = (k) => setSections({ ...sections, [k]: !sections[k] });

  const generatePdf = async () => {
    setGenerating(true);
    try {
      const chosen = Object.keys(sections).filter((k) => sections[k]);
      const res = await exportPdfApi(chosen);
      const url = res.data.download_url;
      const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL.replace(/\/api$/, '')}${url}`;
      const blob = await axios.get(fullUrl, { headers: { Authorization: `Bearer ${getAccessToken()}` }, responseType: 'blob' });
      const dl = window.URL.createObjectURL(blob.data);
      const a = document.createElement('a');
      a.href = dl;
      a.download = `report-${Date.now()}.pdf`;
      a.click();
      window.URL.revokeObjectURL(dl);
      toast.success('Report generated');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not generate report');
    } finally {
      setGenerating(false);
    }
  };

  const downloadCsv = async (type) => {
    try {
      const res = await axios.get(exportCsvUrl(type), { headers: { Authorization: `Bearer ${getAccessToken()}` }, responseType: 'blob' });
      const dl = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = dl;
      a.download = `${type}.csv`;
      a.click();
      window.URL.revokeObjectURL(dl);
    } catch (err) {
      toast.error('Download failed');
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Exports</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Download branded reports and raw data.</p>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center"><FileText className="h-5 w-5 mr-2" /> PDF Report</h2>
        <div className="space-y-2 mb-4">
          {['summary', 'top_rules', 'top_products'].map((k) => (
            <label key={k} className="flex items-center space-x-2">
              <input type="checkbox" checked={sections[k]} onChange={() => toggle(k)} />
              <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">{k.replace('_', ' ')}</span>
            </label>
          ))}
        </div>
        <button onClick={generatePdf} disabled={generating} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg disabled:opacity-60">
          {generating ? 'Generating...' : 'Generate PDF'}
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center"><FileDown className="h-5 w-5 mr-2" /> CSV Exports</h2>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => downloadCsv('summary')} className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-gray-900 dark:text-white">Summary CSV</button>
          <button onClick={() => downloadCsv('top_products')} className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-gray-900 dark:text-white">Top products CSV</button>
          <button onClick={() => downloadCsv('raw')} className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-gray-900 dark:text-white">Raw (first 50k rows)</button>
        </div>
      </div>
    </div>
  );
};
