import type { components } from "./generated/schema";

export type ApiSchemas = components["schemas"];
export type Principal = ApiSchemas["PrincipalResponse"];
export type Session = ApiSchemas["SessionResponse"];
export type CatalogEntry = ApiSchemas["CatalogEntryResponse"];
export type BookCopy = ApiSchemas["BookCopyResponse"];
export type LoanView = ApiSchemas["LoanViewResponse"];
export type ReservationView = ApiSchemas["ReservationViewResponse"];
export type FineView = ApiSchemas["FineViewResponse"];
export type BookRequestView = ApiSchemas["BookRequestViewResponse"];
export type FeedbackView = ApiSchemas["FeedbackViewResponse"];
export type Recommendation = ApiSchemas["RecommendationResponse"];
export type PopularBook = ApiSchemas["PopularBookResponse"];
export type OperationalReport = ApiSchemas["OperationalReportResponse"];
export type UserRole = ApiSchemas["UserRole"];

export type ApiErrorKind =
  | "authentication"
  | "conflict"
  | "database_unavailable"
  | "forbidden"
  | "network"
  | "rate_limited"
  | "service_warming"
  | "unexpected"
  | "validation";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly kind: ApiErrorKind,
    public readonly status?: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
