/*
  home.js
  Purpose: Behaviors specific to home.html
  - Initialize DataTables for uploaded CSV
  - Enhanced file input functionality
  - File name display updates
*/

onReady(function () {
    // Enhanced file input functionality
    const fileInput = document.getElementById('csvFileInput');
    const fileLabel = document.querySelector('.file-input-label');
    const fileText = document.querySelector('.file-text');
    
    if (fileInput && fileLabel && fileText) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                fileText.textContent = file.name;
                fileLabel.classList.add('file-selected');
                
                // Add visual feedback
                fileLabel.style.borderColor = 'var(--success)';
                fileLabel.style.background = 'var(--success-light)';
                
                // Update file info section if it exists
                const fileInfo = document.querySelector('.file-info');
                if (fileInfo) {
                    const filenameText = fileInfo.querySelector('.filename-text');
                    if (filenameText) {
                        filenameText.textContent = file.name;
                    }
                }
            } else {
                fileText.textContent = 'Choose CSV File';
                fileLabel.classList.remove('file-selected');
                fileLabel.style.borderColor = 'var(--primary)';
                fileLabel.style.background = 'var(--input-bg)';
            }
        });
        
        // Drag and drop functionality
        fileLabel.addEventListener('dragover', function(e) {
            e.preventDefault();
            fileLabel.classList.add('drag-over');
        });
        
        fileLabel.addEventListener('dragleave', function(e) {
            e.preventDefault();
            fileLabel.classList.remove('drag-over');
        });
        
        fileLabel.addEventListener('drop', function(e) {
            e.preventDefault();
            fileLabel.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
                    fileInput.files = files;
                    fileInput.dispatchEvent(new Event('change'));
                } else {
                    alert('Please select a CSV file.');
                }
            }
        });
    }
    
    // Initialize DataTable on home page
    const tableEl = document.querySelector("#csvTableContainer table") || document.getElementById("csvTable");
    if (tableEl) {
        if (tableEl.parentElement && tableEl.parentElement.id === "csvTableContainer") {
            $(tableEl).DataTable({
                pageLength: 5,
                lengthMenu: [5, 10, 20, 50],
                autoWidth: false,
                responsive: true,
                language: {
                    search: "Search:",
                    lengthMenu: "Show _MENU_ entries",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                    infoEmpty: "Showing 0 to 0 of 0 entries",
                    infoFiltered: "(filtered from _MAX_ total entries)",
                    paginate: {
                        first: "First",
                        last: "Last",
                        next: "Next",
                        previous: "Previous"
                    }
                },
                dom: '<"top"lf>rt<"bottom"ip><"clear">',
                initComplete: function() {
                    // Add custom styling after initialization
                    this.api().columns().every(function() {
                        const column = this;
                        const header = $(column.header());
                        header.addClass('text-center');
                    });
                }
            });
        } else {
            $.ajax({
                url: '/data',
                type: 'GET',
                dataType: 'json',
                success: function (json) {
                    if (!json.columns || json.columns.length === 0) return;
                    $('#csvTable').DataTable({
                        serverSide: true,
                        processing: true,
                        ajax: '/data',
                        pageLength: 5,
                        lengthMenu: [5, 10, 20, 50],
                        autoWidth: false,
                        responsive: true,
                        columns: json.columns,
                        columnDefs: [{ targets: '_all', defaultContent: "" }],
                        language: {
                            search: "Search:",
                            lengthMenu: "Show _MENU_ entries",
                            info: "Showing _START_ to _END_ of _TOTAL_ entries",
                            infoEmpty: "Showing 0 to 0 of 0 entries",
                            infoFiltered: "(filtered from _MAX_ total entries)",
                            paginate: {
                                first: "First",
                                last: "Last",
                                next: "Next",
                                previous: "Previous"
                            }
                        },
                        dom: '<"top"lf>rt<"bottom"ip><"clear">'
                    });
                }
            });
        }
    }
    
    // Add smooth scrolling for better UX
    const actionButton = document.querySelector('.btn.large');
    if (actionButton) {
        actionButton.addEventListener('click', function(e) {
            // Add a small delay to show the click effect
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    }
    
    // Add animation to stat cards
    const statCards = document.querySelectorAll('.stat-card');
    if (statCards.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'slideInUp 0.6s ease-out';
                }
            });
        }, { threshold: 0.1 });
        
        statCards.forEach(card => {
            observer.observe(card);
        });
    }
});


