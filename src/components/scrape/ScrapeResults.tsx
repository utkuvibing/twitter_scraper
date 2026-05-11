import { useState, useMemo, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { invoke } from '@tauri-apps/api/core';
import { useScrapeStore } from '../../stores/scrapeStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { FileText, FileJson, FileType, Download, Loader2 } from 'lucide-react';
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle } from 'docx';

type SortField = 'date' | 'likes' | 'retweets' | 'replies' | 'views';
type SortDirection = 'asc' | 'desc';
type ExportFormat = 'json' | 'markdown' | 'word';
const EXPORT_SCHEMA_VERSION = '0.2';

const toIsoDate = (date: number | string | null | undefined) => {
  if (date === null || date === undefined || date === '') return null;
  const parsed = new Date(date);
  return Number.isNaN(parsed.getTime()) ? String(date) : parsed.toISOString();
};

function ScrapeResults() {
  const { t } = useTranslation();
  const { tweets, reset } = useScrapeStore();

  const { outputDir } = useSettingsStore();

  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [expandedTweetId, setExpandedTweetId] = useState<string | null>(null);
  const [exportResults, setExportResults] = useState<{ format: string; path: string }[]>([]);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  // File naming & multi-format selection
  const target = useScrapeStore((s) => s.scrapeConfig?.target || 'export');
  const [filename, setFilename] = useState('');
  const [selectedFormats, setSelectedFormats] = useState<Record<ExportFormat, boolean>>({
    json: true,
    markdown: false,
    word: false,
  });

  // Initialize filename from target
  useEffect(() => {
    const now = new Date();
    const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    setFilename(`${target}_${dateStr}`);
  }, [target]);

  // Calculate summary stats
  const stats = useMemo(() => {
    if (tweets.length === 0) {
      return {
        total: 0,
        avgLikes: 0,
        avgRetweets: 0,
        avgReplies: 0,
        dateRange: { start: '', end: '' },
      };
    }

    const sortedByDate = [...tweets].sort((a, b) => a.date - b.date);
    const totalLikes = tweets.reduce((sum, t) => sum + t.likes, 0);
    const totalRetweets = tweets.reduce((sum, t) => sum + t.retweets, 0);
    const totalReplies = tweets.reduce((sum, t) => sum + t.replies, 0);

    return {
      total: tweets.length,
      avgLikes: Math.round(totalLikes / tweets.length),
      avgRetweets: Math.round(totalRetweets / tweets.length),
      avgReplies: Math.round(totalReplies / tweets.length),
      dateRange: {
        start: sortedByDate[0].date_str,
        end: sortedByDate[sortedByDate.length - 1].date_str,
      },
    };
  }, [tweets]);

  // Sort tweets
  const sortedTweets = useMemo(() => {
    const sorted = [...tweets].sort((a, b) => {
      let aVal: any, bVal: any;

      switch (sortField) {
        case 'date':
          aVal = a.date;
          bVal = b.date;
          break;
        case 'likes':
          aVal = a.likes;
          bVal = b.likes;
          break;
        case 'retweets':
          aVal = a.retweets;
          bVal = b.retweets;
          break;
        case 'replies':
          aVal = a.replies;
          bVal = b.replies;
          break;
        case 'views':
          aVal = a.views;
          bVal = b.views;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [tweets, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Generate JSON content from tweets
  const generateJson = useCallback(() => {
    const data = {
      schema_version: EXPORT_SCHEMA_VERSION,
      source: 'x.com',
      scrape_type: useScrapeStore.getState().scrapeConfig?.type || 'profile',
      user: `@${target}`,
      target,
      exported_at: new Date().toISOString(),
      total_tweets: tweets.length,
      tweets: tweets.map((t) => ({
        id: t.id,
        text: t.text,
        date: toIsoDate(t.date),
        date_str: t.date_str,
        url: t.tweet_url,
        tweet_url: t.tweet_url,
        has_media: t.media_urls.length > 0,
        media_urls: t.media_urls,
        has_article: t.has_article,
        needs_full_text: false,
        likes: t.likes,
        retweets: t.retweets,
        replies: t.replies,
        views: t.views,
      })),
    };
    return JSON.stringify(data, null, 2);
  }, [tweets, target]);

  // Generate Markdown content from tweets
  const generateMarkdown = useCallback(() => {
    const lines: string[] = [];
    lines.push(`# @${target} - Tweet Archive\n`);
    lines.push(`**Schema:** ${EXPORT_SCHEMA_VERSION}\n`);
    lines.push(`**Total:** ${tweets.length} tweets\n`);
    lines.push(`**Date:** ${new Date().toLocaleDateString()}\n`);
    lines.push('---\n');

    tweets.forEach((t, i) => {
      lines.push(`## Tweet #${i + 1}\n`);
      lines.push(`**Date:** ${t.date_str}\n`);
      if (t.text) lines.push(`\n${t.text}\n`);
      if (t.media_urls.length > 0) lines.push(`\n**Media:** ${t.media_urls.length} file(s)\n`);
      lines.push(`\n**Likes:** ${t.likes} | **RTs:** ${t.retweets} | **Replies:** ${t.replies} | **Views:** ${t.views}\n`);
      lines.push(`\n[Tweet Link](${t.tweet_url})\n`);
      lines.push('\n---\n');
    });

    return lines.join('\n');
  }, [tweets, target]);

  // Generate DOCX content from tweets (returns base64 string)
  const generateDocx = useCallback(async (): Promise<string> => {
    const children: Paragraph[] = [];

    // Title
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: `@${target} - Tweet Archive`, bold: true, size: 32 })],
    }));

    // Summary
    children.push(new Paragraph({
      children: [new TextRun({ text: `Total: ${tweets.length} tweets`, size: 22 })],
      spacing: { after: 100 },
    }));
    children.push(new Paragraph({
      children: [new TextRun({ text: `Date: ${new Date().toLocaleDateString()}`, size: 22 })],
      spacing: { after: 200 },
    }));

    // Separator
    children.push(new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: '999999' } },
      spacing: { after: 200 },
      children: [],
    }));

    // Tweets
    tweets.forEach((t, i) => {
      children.push(new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun({ text: `Tweet #${i + 1}`, bold: true, size: 26 })],
        spacing: { before: 300 },
      }));

      children.push(new Paragraph({
        children: [new TextRun({ text: `Date: ${t.date_str}`, bold: true, size: 20, color: '666666' })],
        spacing: { after: 100 },
      }));

      if (t.text) {
        children.push(new Paragraph({
          children: [new TextRun({ text: t.text, size: 22 })],
          spacing: { after: 100 },
        }));
      }

      if (t.media_urls.length > 0) {
        children.push(new Paragraph({
          children: [new TextRun({ text: `Media: ${t.media_urls.length} file(s)`, italics: true, size: 20, color: '888888' })],
          spacing: { after: 50 },
        }));
      }

      children.push(new Paragraph({
        children: [
          new TextRun({ text: `Likes: ${t.likes}  |  RTs: ${t.retweets}  |  Replies: ${t.replies}  |  Views: ${t.views}`, size: 20, color: '555555' }),
        ],
        spacing: { after: 50 },
      }));

      children.push(new Paragraph({
        children: [new TextRun({ text: t.tweet_url, size: 18, color: '1d9bf0' })],
        spacing: { after: 100 },
      }));

      // Separator between tweets
      children.push(new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: 'DDDDDD' } },
        spacing: { after: 100 },
        children: [],
      }));
    });

    const doc = new Document({
      sections: [{
        properties: {},
        children,
      }],
    });

    const blob = await Packer.toBlob(doc);
    const arrayBuffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }, [tweets, target]);

  const handleExportAll = useCallback(async () => {
    const formats = (Object.entries(selectedFormats) as [ExportFormat, boolean][])
      .filter(([, selected]) => selected)
      .map(([fmt]) => fmt);

    if (formats.length === 0) return;

    setExportResults([]);
    setExportError(null);
    setIsExporting(true);

    const results: { format: string; path: string }[] = [];

    for (const fmt of formats) {
      try {
        if (fmt === 'word') {
          // Binary format - use base64 command
          const contentBase64 = await generateDocx();
          const path = await invoke<string>('save_binary_export_file', {
            filename: filename.trim() || `${target}_export`,
            target,
            format: 'docx',
            contentBase64,
            outputDir: outputDir || null,
          });
          results.push({ format: 'docx', path });
        } else {
          // Text formats
          const content = fmt === 'json' ? generateJson() : generateMarkdown();
          const formatCode = fmt === 'json' ? 'json' : 'md';

          const path = await invoke<string>('save_export_file', {
            filename: filename.trim() || `${target}_export`,
            target,
            format: formatCode,
            content,
            outputDir: outputDir || null,
          });

          results.push({ format: formatCode, path });
        }
      } catch (err) {
        setExportError(typeof err === 'string' ? err : String(err));
        break;
      }
    }

    setExportResults(results);
    setIsExporting(false);
  }, [selectedFormats, target, filename, outputDir, generateJson, generateMarkdown, generateDocx]);

  const toggleFormat = (fmt: ExportFormat) => {
    setSelectedFormats((prev) => ({ ...prev, [fmt]: !prev[fmt] }));
  };

  const anyFormatSelected = Object.values(selectedFormats).some(Boolean);

  const toggleExpand = (tweetId: string) => {
    setExpandedTweetId(expandedTweetId === tweetId ? null : tweetId);
  };

  const handleNewScrape = () => {
    reset();
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <span className="text-x-gray">⇅</span>;
    return sortDirection === 'asc' ? (
      <span className="text-x-blue">↑</span>
    ) : (
      <span className="text-x-blue">↓</span>
    );
  };

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-x-light mb-2">
              Scrape Results
            </h1>
            <p className="text-x-gray">
              {stats.dateRange.start} - {stats.dateRange.end}
            </p>
          </div>

        </div>

        {/* Export Panel */}
        <div className="mb-6 bg-x-dark/60 border border-x-border/40 rounded-xl p-5 space-y-4">
          {/* File name */}
          <div>
            <label className="block text-xs font-medium text-x-gray mb-1.5">
              Name your file
            </label>
            <input
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              placeholder="my_scrape"
              className="w-full bg-x-darker/80 border border-x-border/40 rounded-lg px-4 py-2.5 text-sm text-x-light placeholder-x-gray/50 focus:outline-none focus:border-x-blue transition-colors"
            />
          </div>

          {/* Format selection */}
          <div>
            <label className="block text-xs font-medium text-x-gray mb-2">
              Export formats
            </label>
            <div className="flex gap-2">
              {([
                { key: 'json' as ExportFormat, label: 'JSON', icon: FileJson },
                { key: 'markdown' as ExportFormat, label: 'Markdown', icon: FileText },
                { key: 'word' as ExportFormat, label: 'Word', icon: FileType },
              ]).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => toggleFormat(key)}
                  disabled={isExporting}
                  className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                    selectedFormats[key]
                      ? 'bg-x-blue text-white'
                      : 'bg-x-darker/80 text-x-gray hover:text-x-light border border-x-border/40'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <Icon size={16} />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Export button */}
          <button
            onClick={handleExportAll}
            disabled={!anyFormatSelected || isExporting}
            className={`w-full py-3 px-5 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
              anyFormatSelected && !isExporting
                ? 'bg-x-blue hover:bg-x-blue/80 text-white'
                : 'bg-x-border/30 text-x-gray cursor-not-allowed'
            }`}
          >
            {isExporting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download size={16} />
                Export {Object.values(selectedFormats).filter(Boolean).length} format(s)
              </>
            )}
          </button>

          {/* Export results */}
          {exportResults.length > 0 && (
            <div className="space-y-2">
              {exportResults.map((result, i) => (
                <div key={i} className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-sm text-green-400 flex items-center justify-between">
                  <span>Exported {result.format.toUpperCase()} to: {result.path}</span>
                </div>
              ))}
            </div>
          )}
          {exportError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400 flex items-center justify-between">
              <span>Export failed: {exportError}</span>
              <button onClick={() => setExportError(null)} className="text-red-400 hover:text-red-300 ml-2">✕</button>
            </div>
          )}
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Total Tweets</p>
            <p className="text-2xl font-bold text-x-light">{stats.total}</p>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Avg Likes</p>
            <p className="text-2xl font-bold text-x-light">{stats.avgLikes}</p>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Avg Retweets</p>
            <p className="text-2xl font-bold text-x-light">{stats.avgRetweets}</p>
          </div>
          <div className="bg-x-dark border border-x-border rounded-lg p-4">
            <p className="text-sm text-x-gray mb-1">Avg Replies</p>
            <p className="text-2xl font-bold text-x-light">{stats.avgReplies}</p>
          </div>
        </div>

        {/* Tweets table */}
        <div className="bg-x-dark border border-x-border rounded-lg overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-x-darker border-b border-x-border text-xs font-medium text-x-gray">
            <button
              onClick={() => handleSort('date')}
              className="col-span-2 text-left hover:text-x-light flex items-center gap-1"
            >
              Date <SortIcon field="date" />
            </button>
            <div className="col-span-4">Tweet</div>
            <button
              onClick={() => handleSort('likes')}
              className="text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              Likes <SortIcon field="likes" />
            </button>
            <button
              onClick={() => handleSort('retweets')}
              className="text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              RTs <SortIcon field="retweets" />
            </button>
            <button
              onClick={() => handleSort('replies')}
              className="text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              Replies <SortIcon field="replies" />
            </button>
            <button
              onClick={() => handleSort('views')}
              className="col-span-2 text-right hover:text-x-light flex items-center justify-end gap-1"
            >
              Views <SortIcon field="views" />
            </button>
          </div>

          {/* Table rows */}
          <div className="max-h-[600px] overflow-y-auto">
            {sortedTweets.map((tweet) => (
              <div
                key={tweet.id}
                className="grid grid-cols-12 gap-4 px-4 py-4 border-b border-x-border hover:bg-x-darker transition-colors cursor-pointer"
                onClick={() => toggleExpand(tweet.id)}
              >
                <div className="col-span-2 text-sm text-x-gray">
                  {tweet.date_str}
                </div>
                <div className="col-span-4">
                  <p
                    className={`text-sm text-x-light ${
                      expandedTweetId === tweet.id ? '' : 'line-clamp-2'
                    }`}
                  >
                    {tweet.text}
                  </p>
                  {expandedTweetId === tweet.id && tweet.media_urls.length > 0 && (
                    <div className="mt-2 text-xs text-x-gray">
                      📎 {tweet.media_urls.length} media file(s)
                    </div>
                  )}
                </div>
                <div className="text-right text-sm text-x-light">
                  {tweet.likes.toLocaleString()}
                </div>
                <div className="text-right text-sm text-x-light">
                  {tweet.retweets.toLocaleString()}
                </div>
                <div className="text-right text-sm text-x-light">
                  {tweet.replies.toLocaleString()}
                </div>
                <div className="col-span-2 text-right text-sm text-x-light">
                  {tweet.views.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* New scrape button */}
        <div className="mt-6 flex justify-center">
          <Link
            to="/scrape"
            onClick={handleNewScrape}
            className="px-6 py-3 bg-x-blue hover:bg-opacity-90 text-white font-semibold rounded-lg transition-all flex items-center gap-2"
          >
            <span>⬇</span>
            <span>New Scrape</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default ScrapeResults;
