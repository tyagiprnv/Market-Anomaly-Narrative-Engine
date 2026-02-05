/**
 * Toast notification system using react-hot-toast
 */
import toast, { Toaster, ToastOptions } from 'react-hot-toast';

/**
 * Toast provider component - add to App root
 * Configures toast appearance and behavior
 */
export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#1f2937', // gray-800
          color: '#f9fafb', // gray-50
          border: '1px solid #374151', // gray-700
          borderRadius: '0.5rem',
          padding: '12px 16px',
        },
        success: {
          iconTheme: {
            primary: '#10b981', // green-500
            secondary: '#f9fafb',
          },
          style: {
            border: '1px solid #10b981',
          },
        },
        error: {
          iconTheme: {
            primary: '#ef4444', // red-500
            secondary: '#f9fafb',
          },
          style: {
            border: '1px solid #ef4444',
          },
        },
        loading: {
          iconTheme: {
            primary: '#3b82f6', // blue-500
            secondary: '#f9fafb',
          },
        },
      }}
    />
  );
}

/**
 * Toast utility functions for consistent messaging
 */

export const showSuccess = (message: string, options?: ToastOptions) => {
  return toast.success(message, options);
};

export const showError = (message: string, options?: ToastOptions) => {
  return toast.error(message, options);
};

export const showLoading = (message: string, options?: ToastOptions) => {
  return toast.loading(message, options);
};

export const showInfo = (message: string, options?: ToastOptions) => {
  return toast(message, {
    icon: 'ℹ️',
    ...options,
  });
};

export const showWarning = (message: string, options?: ToastOptions) => {
  return toast(message, {
    icon: '⚠️',
    style: {
      border: '1px solid #f59e0b', // amber-500
    },
    ...options,
  });
};

/**
 * Dismiss a toast by ID
 */
export const dismissToast = (toastId: string) => {
  toast.dismiss(toastId);
};

/**
 * Dismiss all toasts
 */
export const dismissAllToasts = () => {
  toast.dismiss();
};

/**
 * Show a promise-based toast that updates based on promise state
 * Useful for async operations like API calls
 */
export const showPromiseToast = <T,>(
  promise: Promise<T>,
  messages: {
    loading: string;
    success: string | ((data: T) => string);
    error: string | ((error: Error) => string);
  },
  options?: ToastOptions
) => {
  return toast.promise(promise, messages, options);
};

/**
 * Show a custom toast with custom JSX
 */
export const showCustomToast = (message: React.ReactNode, options?: ToastOptions) => {
  return toast.custom(message, options);
};

// Re-export the base toast for advanced use cases
export { toast };
