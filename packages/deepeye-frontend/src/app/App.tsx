import { Router } from './router'
import { ToastContainer } from '@/shared/components'
import { useToastStore } from '@/store'

function App() {
  const { toasts, removeToast } = useToastStore()

  return (
    <>
      <Router />
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </>
  )
}

export default App

