; (function () {
  const panels = Array.from(document.querySelectorAll('.pdf-panel'))
  if (!panels.length) return

  if (!window['pdfjsLib']) {
    panels.forEach(function (panel) {
      const loadingEl = panel.querySelector('.pdf-loading')
      const errorEl = panel.querySelector('.pdf-error')
      if (loadingEl) loadingEl.style.display = 'none'
      if (errorEl) {
        errorEl.textContent = 'PDF viewer library failed to load.'
        errorEl.hidden = false
      }
    })
    return
  }

  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'

  const viewers = {}

  function createViewer(panel) {
    const id = panel.getAttribute('data-pdf-id')
    const url = panel.getAttribute('data-pdf-url')
    const canvas = panel.querySelector('.pdf-canvas')
    const ctx = canvas.getContext('2d')
    const loadingEl = panel.querySelector('.pdf-loading')
    const errorEl = panel.querySelector('.pdf-error')
    const pageLabel = panel.querySelector('[data-page-label]')
    const prevBtn = panel.querySelector('[data-action=\"prev\"]')
    const nextBtn = panel.querySelector('[data-action=\"next\"]')

    const state = {
      pdfDoc: null,
      page: 1,
      pages: 0,
      scale: 1.0,
      rendering: false,
      pendingPage: null,
    }

    function setLoading(loading) {
      if (!loadingEl) return
      if (loading) {
        loadingEl.style.display = 'flex'
        if (errorEl) errorEl.hidden = true
      } else {
        loadingEl.style.display = 'none'
      }
    }

    function setError(msg) {
      if (!errorEl) return
      errorEl.textContent = msg || 'Unable to load PDF.'
      errorEl.hidden = false
      errorEl.style.display = 'flex'
      if (loadingEl) loadingEl.style.display = 'none'
    }

    function updateControls() {
      if (!state.pages) {
        if (pageLabel) pageLabel.textContent = '—'
        if (prevBtn) prevBtn.disabled = true
        if (nextBtn) nextBtn.disabled = true
        return
      }
      if (pageLabel) {
        pageLabel.textContent = 'Page ' + state.page + ' / ' + state.pages
      }
      if (prevBtn) prevBtn.disabled = state.page <= 1
      if (nextBtn) nextBtn.disabled = state.page >= state.pages
    }

    function getScale(viewportWidth) {
      const container = panel.querySelector('.pdf-body')
      const maxWidth = container.clientWidth || viewportWidth
      const ratio = maxWidth / viewportWidth
      return Math.max(Math.min(ratio, 2.0), 0.6)
    }

    function renderPage(num) {
      if (state.rendering) {
        state.pendingPage = num
        return
      }
      state.rendering = true
      setLoading(true)

      state.pdfDoc
        .getPage(num)
        .then(function (page) {
          const baseViewport = page.getViewport({ scale: 1.0 })
          state.scale = getScale(baseViewport.width)
          const viewport = page.getViewport({ scale: state.scale })
          canvas.height = viewport.height
          canvas.width = viewport.width
          const renderContext = { canvasContext: ctx, viewport: viewport }

          return page.render(renderContext).promise
        })
        .then(function () {
          state.rendering = false
          setLoading(false)
          state.page = num
          updateControls()
          if (state.pendingPage !== null && state.pendingPage !== num) {
            const next = state.pendingPage
            state.pendingPage = null
            renderPage(next)
          } else {
            state.pendingPage = null
          }
        })
        .catch(function () {
          state.rendering = false
          setError('Error rendering page.')
        })
    }

    function load() {
      setLoading(true)
      pdfjsLib
        .getDocument({ url: url })
        .promise.then(function (pdfDoc) {
          state.pdfDoc = pdfDoc
          state.pages = pdfDoc.numPages
          updateControls()
          renderPage(1)
        })
        .catch(function () {
          setError('Failed to load PDF.')
        })
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        if (!state.pdfDoc || state.page <= 1) return
        renderPage(state.page - 1)
      })
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (!state.pdfDoc || state.page >= state.pages) return
        renderPage(state.page + 1)
      })
    }

    viewers[id] = { state: state, renderPage: renderPage }
    load()
  }

  panels.forEach(createViewer)

  let resizeTimeout = null
  window.addEventListener('resize', function () {
    if (resizeTimeout) clearTimeout(resizeTimeout)
    resizeTimeout = setTimeout(function () {
      Object.values(viewers).forEach(function (viewer) {
        if (!viewer.state.pdfDoc || !viewer.state.pages) return
        viewer.renderPage(viewer.state.page)
      })
    }, 200)
  })
})()


