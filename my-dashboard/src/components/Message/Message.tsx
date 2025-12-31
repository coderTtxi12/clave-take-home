'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { MessageProps } from '@/types';
import styles from './Message.module.css';
import 'highlight.js/styles/github-dark.css';

export const Message: React.FC<MessageProps> = ({ message }) => {
  const { text, sender, timestamp, isStreaming, files = [] } = message;
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  return (
    <div className={`${styles.message} ${sender === 'user' ? styles.user : styles.ai}`}>
      {files.length > 0 && (
        <div className={styles.messageFilesContainer}>
          <div className={styles.messageFiles}>
            {files.map((file, index) => (
              <div key={index} className={styles.messageFile}>
                <div className={styles.filePreview}>
                  {file.type?.startsWith('image/') ? (
                    <img 
                      src={URL.createObjectURL(file)} 
                      alt={file.name}
                      onClick={() => setSelectedImage(URL.createObjectURL(file))}
                      style={{ cursor: 'pointer' }}
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        if (target.nextSibling) {
                          (target.nextSibling as HTMLElement).style.display = 'flex';
                        }
                      }}
                    />
                  ) : null}
                  <div 
                    className={styles.fileIcon} 
                    style={{ display: file.type?.startsWith('image/') ? 'none' : 'flex' }}
                  >
                    <span className="material-icons">
                      {file.type?.startsWith('image/') ? 'image' : 'description'}
                    </span>
                  </div>
                </div>
                <div className={styles.fileInfo}>
                  <span className={styles.fileName}>{file.name}</span>
                  <span className={styles.fileSize}>
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {text ? (
        <>
          <div className={styles.messageContent}>
            <div className={styles.messageText}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <pre className={styles.codeBlock}>
                        <code className={className} {...props}>
                          {children}
                        </code>
                      </pre>
                    ) : (
                      <code className={styles.inlineCode} {...props}>
                        {children}
                      </code>
                    );
                  },
                  pre({ children }) {
                    return <div className={styles.codeWrapper}>{children}</div>;
                  }
                }}
              >
                {text}
              </ReactMarkdown>
              {isStreaming && <span className={styles.streamingCursor}>|</span>}
            </div>
          </div>
          {sender === 'user' ? (
            <div className={styles.messageTimeOnly}>{timestamp}</div>
          ) : (
            <div className={styles.messageTime}>{timestamp}</div>
          )}
        </>
      ) : (
        <div className={styles.messageTimeOnly}>{timestamp}</div>
      )}
      
      {/* Image Preview Modal */}
      {selectedImage && (
        <div className={styles.imagePreviewModal} onClick={() => setSelectedImage(null)}>
          <div className={styles.imagePreviewContent} onClick={(e) => e.stopPropagation()}>
            <button 
              className={styles.imagePreviewClose}
              onClick={() => setSelectedImage(null)}
            >
              <span className="material-icons">close</span>
            </button>
            <img 
              src={selectedImage} 
              alt="Preview" 
              className={styles.imagePreviewLarge}
            />
          </div>
        </div>
      )}
    </div>
  );
};

