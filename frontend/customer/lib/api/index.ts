/**
 * API Module Exports
 */

// Client
export {
  api,
  apiRequest,
  getAccessToken,
  getRefreshToken,
  getTenantId,
  setTokens,
  setTenantId,
  clearTokens,
  clearAll,
  refreshAccessToken,
  getBackendBaseUrl,
  getMediaUrl,
} from './client';

export type { TokenPair, ApiError } from './client';

// Error Handler
export {
  ErrorCode,
  isApiError,
  isAuthError,
  isForbiddenError,
  isValidationError,
  isNotFoundError,
  isBusinessError,
  isServerError,
  getErrorMessage,
  getDefaultMessageForCode,
  extractFormErrors,
  getFirstFormError,
  handleApiError,
  showErrorToast,
  handleFormError,
  safeApiCall,
} from './error-handler';

export type {
  ErrorCodeType,
  ApiErrorWithCode,
  FormErrors,
  HandleErrorOptions,
} from './error-handler';

// Types - re-export all types
export * from './types';
