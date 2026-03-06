; (function () {
  const panels = Array.from(document.querySelectorAll('.pdf-panel'))
  if (!panels.length) return

  if (!window.pdfjsLib) {
    panels.forEach(function (p) {
      const err = p.querySelector('.pdf-error')
      p.querySelector('.pdf-loading').style.display = 'none'
      if (err) { err.textContent = 'PDF viewer library failed to load.'; err.hidden = false }
    })
    return
  }

  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'

  var loading = 0
  var queue = []

  function dequeue() {
    if (loading >= 2 || !queue.length) return
    var init = queue.shift()
    loading++
    init()
  }

  function createViewer(panel) {
    var id = panel.getAttribute('data-pdf-id')
    var url = panel.getAttribute('data-pdf-url')
    var canvas = panel.querySelector('.pdf-canvas')
    var ctx = canvas.getContext('2d')
    var loadingEl = panel.querySelector('.pdf-loading')
    var errorEl = panel.querySelector('.pdf-error')
    var pageLabel = panel.querySelector('[data-page-label]')
    var prevBtn = panel.querySelector('[data-action="prev"]')
    var nextBtn = panel.querySelector('[data-action="next"]')
    var body = panel.querySelector('.pdf-body')

    var pdfDoc = null
    var currentPage = 1
    var totalPages = 0
    var cachedScale = null
    var rendering = false
    var pendingPage = null

    function showLoading(on) {
      loadingEl.style.display = on ? 'flex' : 'none'
      if (on && errorEl) errorEl.hidden = true
    }

    function showError(msg) {
      if (errorEl) { errorEl.textContent = msg || 'Unable to load PDF.'; errorEl.hidden = false; errorEl.style.display = 'flex' }
      loadingEl.style.display = 'none'
    }

    function syncControls() {
      if (!totalPages) {
        if (pageLabel) pageLabel.textContent = '—'
        if (prevBtn) prevBtn.disabled = true
        if (nextBtn) nextBtn.disabled = true
        return
      }
      if (pageLabel) pageLabel.textContent = 'Page ' + currentPage + ' / ' + totalPages
      if (prevBtn) prevBtn.disabled = currentPage <= 1
      if (nextBtn) nextBtn.disabled = currentPage >= totalPages
    }

    function computeScale(nativeWidth) {
      return Math.max(Math.min((body.clientWidth || nativeWidth) / nativeWidth, 2.0), 0.6)
    }

    function renderPage(num) {
      if (rendering) { pendingPage = num; return }
      rendering = true
      showLoading(true)

      pdfDoc.getPage(num).then(function (page) {
        var native = page.getViewport({ scale: 1.0 })
        if (!cachedScale) cachedScale = computeScale(native.width)
        var vp = page.getViewport({ scale: cachedScale })
        canvas.width = vp.width
        canvas.height = vp.height
        return page.render({ canvasContext: ctx, viewport: vp }).promise
      }).then(function () {
        rendering = false
        showLoading(false)
        currentPage = num
        syncControls()
        if (pendingPage !== null && pendingPage !== num) {
          var next = pendingPage
          pendingPage = null
          renderPage(next)
        } else {
          pendingPage = null
        }
      }).catch(function () {
        rendering = false
        showError('Error rendering page.')
      })
    }

    function invalidateScale() {
      cachedScale = null
    }

    if (prevBtn) prevBtn.addEventListener('click', function () {
      if (!pdfDoc || currentPage <= 1) return
      renderPage(currentPage - 1)
    })

    if (nextBtn) nextBtn.addEventListener('click', function () {
      if (!pdfDoc || currentPage >= totalPages) return
      renderPage(currentPage + 1)
    })

    return {
      enqueue: function () {
        queue.push(function () {
          showLoading(true)
          pdfjsLib.getDocument({ url: url, rangeChunkSize: 65536, disableAutoFetch: false, disableStream: false })
            .promise.then(function (doc) {
              pdfDoc = doc
              totalPages = doc.numPages
              syncControls()
              renderPage(1)
            }).catch(function () {
              showError('Failed to load PDF.')
            }).finally(function () {
              loading--
              dequeue()
            })
        })
        dequeue()
      },
      invalidateScale: invalidateScale,
      rerender: function () { if (pdfDoc && totalPages) renderPage(currentPage) },
    }
  }

  var viewers = panels.map(function (panel) {
    var v = createViewer(panel)

    var observer = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        observer.disconnect()
        v.enqueue()
      }
    }, { rootMargin: '200px' })

    observer.observe(panel)
    return v
  })

  var resizeTimer = null
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer)
    resizeTimer = setTimeout(function () {
      viewers.forEach(function (v) { v.invalidateScale(); v.rerender() })
    }, 250)
  })
}())
