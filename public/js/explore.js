document.addEventListener("DOMContentLoaded", () => {
  const documentListContainer = document.getElementById("document-list");

  if (documentListContainer) {
    fetchAndDisplayDocuments();
  }
});

async function fetchAndDisplayDocuments() {
  const container = document.getElementById("document-list");

  try {
    const response = await fetch("/documents/");

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const documents = await response.json();

    if (documents.length === 0) {
      container.innerHTML =
        "<p>Chưa có tài liệu nào được upload cho mục này.</p>";
      return;
    }

    container.innerHTML = "";

    documents.forEach((doc) => {
      const documentCardHTML = `
            <div class="document-card-large">
                <div class="document-icon-large">
                    ${getIconForFile(doc.content_type)} </div>
                <div class="document-content-large">
                    <h3>${doc.documentTitle}</h3>
                    <p class="document-description">${doc.description}</p>
                    
                    <div class="document-meta">
                        <span class="tag">${doc.documentType}</span>
                        ${generateTagsHTML(doc.tags)}
                    </div>
                    
                    <div class="document-info">
                        <span>
                            <i class="far fa-calendar"></i> 
                            ${new Date(doc.uploaded_at).toLocaleDateString()}
                        </span>
                        <span>
                            <i class="fas fa-university"></i>
                            ${doc.university}
                        </span>
                         <span>
                            <i class="fas fa-book"></i>
                            ${doc.course}
                        </span>
                    </div>
                </div>
                <div class="document-actions-large">
                    <button class="icon-btn-large vote-btn ${doc.has_voted ? 'voted' : ''}" data-doc-id="${doc.id || doc._id || ''}" title="Vote">
                        <i class="fas fa-arrow-up"></i>
                        <span class="vote-count">${doc.vote_count !== undefined ? doc.vote_count : 0}</span>
                    </button>
                    <button class="icon-btn-large comment-btn" data-doc-id="${doc.id || doc._id || ''}" title="Comments">
                        <i class="fas fa-comment"></i>
                        <span class="comment-count">${doc.comment_count !== undefined ? doc.comment_count : 0}</span>
                    </button>
                    <a href="/api/documents/${doc.id || doc._id || ''}/file" target="_blank" class="btn btn-primary">
                        <i class="fas fa-download"></i>
                        Download
                    </a>
                </div>
            </div>
            `;

      container.insertAdjacentHTML("beforeend", documentCardHTML);
      
      const docId = doc.id || doc._id || '';
      if (docId) {
        checkUserVoteStatus(docId);
      }
    });
    
    attachCommentButtonListeners();
    attachVoteButtonListeners();
  } catch (error) {
    console.error("Lỗi khi tải tài liệu:", error);
    container.innerHTML =
      "<p style='color: red;'>Không thể tải danh sách tài liệu. Vui lòng thử lại.</p>";
  }
}

/**
 * Attach event listeners to all comment buttons
 */
function attachCommentButtonListeners() {
  const commentButtons = document.querySelectorAll('.comment-btn');
  commentButtons.forEach(button => {
    button.addEventListener('click', function() {
      const docId = this.getAttribute('data-doc-id');
      if (!docId || docId === 'undefined' || docId === '') {
        console.error('Invalid document ID');
        alert('Error: Document ID not found. Please refresh the page.');
        return;
      }
      openCommentsModal(docId);
    });
  });
}

/**
 * Attach event listeners to all vote buttons
 */
function attachVoteButtonListeners() {
  const voteButtons = document.querySelectorAll('.vote-btn');
  voteButtons.forEach(button => {
    button.addEventListener('click', async function() {
      const docId = this.getAttribute('data-doc-id');
      if (!docId || docId === 'undefined' || docId === '') {
        console.error('Invalid document ID');
        return;
      }
      
      // Check if user is logged in
      const token = getToken ? getToken() : null;
      if (!token) {
        alert('Please log in to vote');
        window.location.href = 'login.html';
        return;
      }
      
      await toggleVote(docId, this);
    });
  });
}

/**
 * Open comments modal and load comments for a document
 */
async function openCommentsModal(docId) {
  const modal = document.getElementById('commentsModal');
  const commentsList = document.getElementById('commentsList');
  const commentForm = document.getElementById('commentForm');
  
  // Store current document ID
  modal.dataset.docId = docId;
  
  // Show modal
  modal.classList.add('active');
  
  // Load comments
  await loadComments(docId);
  
  // Reset form
  commentForm.reset();
}

/**
 * Close comments modal
 */
function closeCommentsModal() {
  const modal = document.getElementById('commentsModal');
  modal.classList.remove('active');
  const commentsList = document.getElementById('commentsList');
  commentsList.innerHTML = '<p class="loading-text">Loading comments...</p>';
}

/**
 * Load comments for a document
 */
async function loadComments(docId) {
  const commentsList = document.getElementById('commentsList');
  
  try {
    const token = getToken ? getToken() : null;
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`/api/documents/${docId}/comments`, {
      method: 'GET',
      headers: headers
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        // No comments yet
        commentsList.innerHTML = '<p class="no-comments">No comments yet. Be the first to comment!</p>';
        return;
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const comments = await response.json();
    
    if (!comments || comments.length === 0) {
      commentsList.innerHTML = '<p class="no-comments">No comments yet. Be the first to comment!</p>';
      return;
    }
    
    // Display comments
    commentsList.innerHTML = '';
    comments.forEach(comment => {
      const commentHTML = createCommentHTML(comment);
      commentsList.insertAdjacentHTML('beforeend', commentHTML);
    });
    
    // Update comment count on the button
    updateCommentCount(docId, comments.length);
    
  } catch (error) {
    console.error('Error loading comments:', error);
    commentsList.innerHTML = '<p class="error-text">Failed to load comments. Please try again.</p>';
  }
}

/**
 * Create HTML for a single comment
 */
function createCommentHTML(comment) {
  const date = new Date(comment.created_at || comment.createdAt || Date.now());
  const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  return `
    <div class="comment-item">
      <div class="comment-avatar">
        <i class="fas fa-user"></i>
      </div>
      <div class="comment-content">
        <div class="comment-header">
          <span class="comment-author">${escapeHtml(comment.author_name || comment.authorName || 'Anonymous')}</span>
          <span class="comment-date">${formattedDate}</span>
        </div>
        <div class="comment-text">${escapeHtml(comment.text || comment.content)}</div>
      </div>
    </div>
  `;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Check if user has voted for a document and update UI
 */
async function checkUserVoteStatus(docId) {
  try {
    const token = getToken ? getToken() : null;
    if (!token) return;
    
    const response = await fetch(`/api/documents/${docId}/votes/check`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      const voteButton = document.querySelector(`.vote-btn[data-doc-id="${docId}"]`);
      if (voteButton) {
        if (data.has_voted) {
          voteButton.classList.add('voted');
        } else {
          voteButton.classList.remove('voted');
        }
      }
    }
  } catch (error) {
    // Silently fail in production
  }
}

/**
 * Toggle vote for a document
 */
async function toggleVote(docId, buttonElement) {
  try {
    const token = getToken ? getToken() : null;
    if (!token) {
      alert('Please log in to vote');
      window.location.href = 'login.html';
      return;
    }
    
    const response = await fetch(`/api/documents/${docId}/votes`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to vote');
    }
    
    const result = await response.json();
    
    // Update vote count
    const voteCountSpan = buttonElement.querySelector('.vote-count');
    if (voteCountSpan) {
      voteCountSpan.textContent = result.vote_count;
    }
    
    // Update voted state
    if (result.has_voted) {
      buttonElement.classList.add('voted');
    } else {
      buttonElement.classList.remove('voted');
    }
    
  } catch (error) {
    console.error('Error toggling vote:', error);
    alert('Failed to vote. Please try again.');
  }
}

/**
 * Update comment count on the button
 */
function updateCommentCount(docId, count) {
  const button = document.querySelector(`.comment-btn[data-doc-id="${docId}"]`);
  if (button) {
    const countSpan = button.querySelector('.comment-count');
    if (countSpan) {
      countSpan.textContent = count;
    }
  }
}

/**
 * Handle comment form submission
 */
document.addEventListener('DOMContentLoaded', () => {
  const commentForm = document.getElementById('commentForm');
  const commentsModal = document.getElementById('commentsModal');
  const closeBtn = document.getElementById('closeCommentsModal');
  
  // Close modal button
  if (closeBtn) {
    closeBtn.addEventListener('click', closeCommentsModal);
  }
  
  // Close modal when clicking outside
  if (commentsModal) {
    commentsModal.addEventListener('click', function(e) {
      if (e.target === this) {
        closeCommentsModal();
      }
    });
  }
  
  // Comment form submission
  if (commentForm) {
    commentForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const docId = commentsModal.dataset.docId;
      const commentText = document.getElementById('commentText').value.trim();
      
      if (!commentText) {
        return;
      }
      
      if (!docId) {
        console.error('No document ID found');
        return;
      }
      
      // Check if user is logged in
      const token = getToken ? getToken() : null;
      if (!token) {
        alert('Please log in to post a comment');
        window.location.href = 'login.html';
        return;
      }
      
      try {
        const response = await fetch(`/api/documents/${docId}/comments`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            text: commentText
          })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to post comment');
        }
        
        // Clear form
        commentForm.reset();
        
        // Reload comments
        await loadComments(docId);
        
      } catch (error) {
        console.error('Error posting comment:', error);
        alert('Failed to post comment. Please try again.');
      }
    });
  }
});

/**
 * Hàm trợ giúp: Tạo các tag HTML từ một chuỗi tags
 * (ví dụ: "python, oop" -> <span...>python</span><span...>oop</span>)
 */
function generateTagsHTML(tagsString) {
  if (!tagsString || tagsString.trim() === "") {
    return ""; // Trả về chuỗi rỗng nếu không có tag
  }

  // Tách chuỗi bằng dấu phẩy, xóa khoảng trắng, và tạo HTML
  return tagsString
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag) // Lọc bỏ các tag rỗng
    .map((tag) => `<span class="tag">${tag}</span>`)
    .join(""); // Nối tất cả lại
}

/**
 * Hàm trợ giúp: Trả về icon dựa trên loại file
 */
function getIconForFile(contentType) {
  if (contentType.includes("pdf")) {
    return '<i class="fas fa-file-pdf"></i>';
  } else if (contentType.includes("word")) {
    return '<i class="fas fa-file-word"></i>';
  } else if (
    contentType.includes("presentation") ||
    contentType.includes("powerpoint")
  ) {
    return '<i class="fas fa-file-powerpoint"></i>';
  } else {
    return '<i class="fas fa-file-alt"></i>'; // Icon chung
  }
}

