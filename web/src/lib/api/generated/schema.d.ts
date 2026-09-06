export interface paths {
    "/api/v1/accounts/bootstrap-administrator": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bootstrap */
        post: operations["bootstrap_api_v1_accounts_bootstrap_administrator_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/deactivate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Deactivate */
        post: operations["deactivate_api_v1_accounts_deactivate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/librarians": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Librarian */
        post: operations["create_librarian_api_v1_accounts_librarians_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/accounts/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register */
        post: operations["register_api_v1_accounts_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Current Session */
        get: operations["current_session_api_v1_auth_session_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/catalog/books": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Browse */
        get: operations["browse_api_v1_catalog_books_get"];
        put?: never;
        /** Add Book */
        post: operations["add_book_api_v1_catalog_books_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/catalog/books/{book_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Book */
        get: operations["get_book_api_v1_catalog_books__book_id__get"];
        /** Update Book */
        put: operations["update_book_api_v1_catalog_books__book_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/catalog/books/{book_id}/copies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Copies */
        get: operations["list_copies_api_v1_catalog_books__book_id__copies_get"];
        put?: never;
        /** Add Copy */
        post: operations["add_copy_api_v1_catalog_books__book_id__copies_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/catalog/copies/{barcode}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Copy */
        patch: operations["update_copy_api_v1_catalog_copies__barcode__patch"];
        trace?: never;
    };
    "/api/v1/circulation/loans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Loans */
        get: operations["loans_api_v1_circulation_loans_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/circulation/loans/checkout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Checkout */
        post: operations["checkout_api_v1_circulation_loans_checkout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/circulation/loans/return": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Return Copy */
        post: operations["return_copy_api_v1_circulation_loans_return_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/circulation/loans/{loan_id}/renew": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Renew */
        post: operations["renew_api_v1_circulation_loans__loan_id__renew_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/circulation/reservations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Reservations */
        get: operations["reservations_api_v1_circulation_reservations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/circulation/reservations/books/{book_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reserve */
        post: operations["reserve_api_v1_circulation_reservations_books__book_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/circulation/reservations/{reservation_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel */
        post: operations["cancel_api_v1_circulation_reservations__reservation_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engagement/book-requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Book Requests */
        get: operations["book_requests_api_v1_engagement_book_requests_get"];
        put?: never;
        /** Submit Request */
        post: operations["submit_request_api_v1_engagement_book_requests_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engagement/book-requests/{request_id}/acquire": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Acquire Request */
        post: operations["acquire_request_api_v1_engagement_book_requests__request_id__acquire_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engagement/book-requests/{request_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review Request */
        post: operations["review_request_api_v1_engagement_book_requests__request_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engagement/feedback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Feedback */
        get: operations["feedback_api_v1_engagement_feedback_get"];
        put?: never;
        /** Submit Feedback */
        post: operations["submit_feedback_api_v1_engagement_feedback_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engagement/feedback/{feedback_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Feedback */
        post: operations["archive_feedback_api_v1_engagement_feedback__feedback_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/engagement/feedback/{feedback_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review Feedback */
        post: operations["review_feedback_api_v1_engagement_feedback__feedback_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/finance/fines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Fines */
        get: operations["fines_api_v1_finance_fines_get"];
        put?: never;
        /** Assess */
        post: operations["assess_api_v1_finance_fines_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/finance/fines/{fine_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Fine */
        get: operations["fine_api_v1_finance_fines__fine_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/finance/fines/{fine_id}/payment": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pay */
        post: operations["pay_api_v1_finance_fines__fine_id__payment_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/finance/fines/{fine_id}/waiver": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Waive */
        post: operations["waive_api_v1_finance_fines__fine_id__waiver_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/insights/operations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Operations */
        get: operations["operations_api_v1_insights_operations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/insights/popular": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Popular */
        get: operations["popular_api_v1_insights_popular_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/insights/recommendations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Recommendations */
        get: operations["recommendations_api_v1_insights_recommendations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Liveness */
        get: operations["liveness_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Readiness */
        get: operations["readiness_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AccountRequest */
        AccountRequest: {
            /** Display Name */
            display_name: string;
            /** Password */
            password: string;
            /** Username */
            username: string;
        };
        /** AcquiredRequest */
        AcquiredRequest: {
            /** Book Id */
            book_id: number;
        };
        /** AcquisitionRequestBody */
        AcquisitionRequestBody: {
            /** Author */
            author: string;
            /** Publication Year */
            publication_year?: number | null;
            /** Title */
            title: string;
        };
        /** BookCopyResponse */
        BookCopyResponse: {
            /** Barcode */
            barcode: string;
            /** Book Id */
            book_id: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Id */
            id: number;
            status: components["schemas"]["BookCopyStatus"];
        };
        /**
         * BookCopyStatus
         * @enum {string}
         */
        BookCopyStatus: "available" | "on_loan" | "lost" | "damaged" | "withdrawn";
        /** BookRequestBody */
        BookRequestBody: {
            /** Author */
            author: string;
            /** Category */
            category?: string | null;
            /** Description */
            description?: string | null;
            /** Isbn */
            isbn?: string | null;
            /** Publication Year */
            publication_year: number;
            /** Title */
            title: string;
        };
        /** BookRequestResponse */
        BookRequestResponse: {
            /** Acquired At */
            acquired_at: string | null;
            /** Acquired Book Id */
            acquired_book_id: number | null;
            /** Acquired By User Id */
            acquired_by_user_id: number | null;
            /** Author */
            author: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Id */
            id: number;
            /** Publication Year */
            publication_year: number | null;
            /** Review Note */
            review_note: string | null;
            /** Reviewed At */
            reviewed_at: string | null;
            /** Reviewed By User Id */
            reviewed_by_user_id: number | null;
            status: components["schemas"]["RequestStatus"];
            /** Title */
            title: string;
            /** User Id */
            user_id: number;
        };
        /** BookRequestViewResponse */
        BookRequestViewResponse: {
            /** Acquired Book Title */
            acquired_book_title: string | null;
            /** Acquisition Actor Username */
            acquisition_actor_username: string | null;
            request: components["schemas"]["BookRequestResponse"];
            /** Reviewer Username */
            reviewer_username: string | null;
            /** Username */
            username: string;
        };
        /** BookResponse */
        BookResponse: {
            /** Author */
            author: string;
            /** Category */
            category: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Description */
            description: string | null;
            /** Id */
            id: number;
            /** Isbn */
            isbn: string | null;
            /** Publication Year */
            publication_year: number;
            /** Title */
            title: string;
        };
        /** CatalogEntryResponse */
        CatalogEntryResponse: {
            /** Available Copies */
            available_copies: number;
            book: components["schemas"]["BookResponse"];
            /** Total Copies */
            total_copies: number;
        };
        /** CheckoutRequest */
        CheckoutRequest: {
            /** Barcode */
            barcode: string;
            /** Borrower Username */
            borrower_username: string;
        };
        /** CopyRequest */
        CopyRequest: {
            /** Barcode */
            barcode: string;
        };
        /** CopyStatusRequest */
        CopyStatusRequest: {
            status: components["schemas"]["BookCopyStatus"];
        };
        /** DeactivateAccountRequest */
        DeactivateAccountRequest: {
            /** Username */
            username: string;
        };
        /** FeedbackRequest */
        FeedbackRequest: {
            /** Content */
            content: string;
        };
        /** FeedbackResponse */
        FeedbackResponse: {
            /** Content */
            content: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Id */
            id: number;
            /** Reviewed At */
            reviewed_at: string | null;
            /** Reviewed By User Id */
            reviewed_by_user_id: number | null;
            status: components["schemas"]["FeedbackStatus"];
            /** User Id */
            user_id: number | null;
        };
        /**
         * FeedbackStatus
         * @enum {string}
         */
        FeedbackStatus: "new" | "reviewed" | "archived";
        /** FeedbackViewResponse */
        FeedbackViewResponse: {
            feedback: components["schemas"]["FeedbackResponse"];
            /** Reviewer Username */
            reviewer_username: string | null;
            /** Username */
            username: string;
        };
        /** FineResponse */
        FineResponse: {
            /** Amount */
            amount: string;
            /**
             * Assessed At
             * Format: date-time
             */
            assessed_at: string;
            /** Id */
            id: number;
            /** Loan Id */
            loan_id: number | null;
            /** Reason */
            reason: string;
            /** Settled At */
            settled_at: string | null;
            status: components["schemas"]["FineStatus"];
            /** User Id */
            user_id: number;
        };
        /**
         * FineSettlementKind
         * @enum {string}
         */
        FineSettlementKind: "payment" | "waiver";
        /**
         * FineStatus
         * @enum {string}
         */
        FineStatus: "outstanding" | "paid" | "waived";
        /** FineViewResponse */
        FineViewResponse: {
            fine: components["schemas"]["FineResponse"];
            settlement: components["schemas"]["SettlementResponse"] | null;
            /** Settlement Actor Username */
            settlement_actor_username: string | null;
            /** Username */
            username: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * HealthCheck
         * @description Public status of one dependency without sensitive details.
         */
        HealthCheck: {
            /** Detail */
            detail: string;
            /** Name */
            name: string;
            /** Ready */
            ready: boolean;
        };
        /**
         * HealthResponse
         * @description Stable health response shared by liveness and readiness.
         */
        HealthResponse: {
            /**
             * Checks
             * @default []
             */
            checks: components["schemas"]["HealthCheck"][];
            /** Environment */
            environment: string;
            /** Status */
            status: string;
            /** Version */
            version: string;
        };
        /** LoanResponse */
        LoanResponse: {
            /** Book Copy Id */
            book_copy_id: number;
            /**
             * Checked Out At
             * Format: date-time
             */
            checked_out_at: string;
            /**
             * Due At
             * Format: date-time
             */
            due_at: string;
            /** Id */
            id: number;
            /** Renewal Count */
            renewal_count: number;
            /** Returned At */
            returned_at: string | null;
            /** User Id */
            user_id: number;
        };
        /** LoanViewResponse */
        LoanViewResponse: {
            assessed_fine: components["schemas"]["FineResponse"] | null;
            book: components["schemas"]["BookResponse"];
            /** Borrower Username */
            borrower_username: string;
            copy: components["schemas"]["BookCopyResponse"];
            /** Is Overdue */
            is_overdue: boolean;
            loan: components["schemas"]["LoanResponse"];
        };
        /** LoginRequest */
        LoginRequest: {
            /** Password */
            password: string;
            /** Username */
            username: string;
        };
        /** ManualFineRequest */
        ManualFineRequest: {
            /** Amount */
            amount: number | string;
            /** Reason */
            reason: string;
            /** Username */
            username: string;
        };
        /** NoteRequest */
        NoteRequest: {
            /** Note */
            note?: string | null;
        };
        /** OperationalReportResponse */
        OperationalReportResponse: {
            /** Active Loans */
            active_loans: number;
            /** Active Reservations */
            active_reservations: number;
            /** Active Users */
            active_users: number;
            /** Available Copies */
            available_copies: number;
            /** Catalog Titles */
            catalog_titles: number;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** New Feedback */
            new_feedback: number;
            /** Outstanding Fine Amount */
            outstanding_fine_amount: string;
            /** Outstanding Fines */
            outstanding_fines: number;
            /** Overdue Loans */
            overdue_loans: number;
            /** Pending Requests */
            pending_requests: number;
            /** Popular Books */
            popular_books: components["schemas"]["PopularBookResponse"][];
            /** Total Copies */
            total_copies: number;
        };
        /** PopularBookResponse */
        PopularBookResponse: {
            /** Available Copies */
            available_copies: number;
            book: components["schemas"]["BookResponse"];
            /** Historical Checkouts */
            historical_checkouts: number;
        };
        /** PrincipalResponse */
        PrincipalResponse: {
            /** Display Name */
            display_name: string;
            role: components["schemas"]["UserRole"];
            /** User Id */
            user_id: number;
            /** Username */
            username: string;
        };
        /** RecommendationResponse */
        RecommendationResponse: {
            /** Available Copies */
            available_copies: number;
            book: components["schemas"]["BookResponse"];
            /** Historical Checkouts */
            historical_checkouts: number;
            /** Reason */
            reason: string;
            /** Score */
            score: number;
        };
        /**
         * RequestStatus
         * @enum {string}
         */
        RequestStatus: "pending" | "approved" | "rejected" | "acquired";
        /** ReservationResponse */
        ReservationResponse: {
            /** Book Id */
            book_id: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Id */
            id: number;
            /** Resolved At */
            resolved_at: string | null;
            status: components["schemas"]["ReservationStatus"];
            /** User Id */
            user_id: number;
        };
        /**
         * ReservationStatus
         * @enum {string}
         */
        ReservationStatus: "active" | "fulfilled" | "cancelled" | "expired";
        /** ReservationViewResponse */
        ReservationViewResponse: {
            /** Book Title */
            book_title: string;
            /** Queue Position */
            queue_position: number | null;
            reservation: components["schemas"]["ReservationResponse"];
        };
        /** ReturnRequest */
        ReturnRequest: {
            /** Barcode */
            barcode: string;
        };
        /** ReviewRequest */
        ReviewRequest: {
            /** Note */
            note?: string | null;
            status: components["schemas"]["RequestStatus"];
        };
        /** SessionResponse */
        SessionResponse: {
            /** Csrf Token */
            csrf_token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            principal: components["schemas"]["PrincipalResponse"];
        };
        /** SettlementResponse */
        SettlementResponse: {
            /** Amount */
            amount: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Fine Id */
            fine_id: number;
            /** Id */
            id: number;
            kind: components["schemas"]["FineSettlementKind"];
            /** Note */
            note: string | null;
            /** Recorded By User Id */
            recorded_by_user_id: number;
        };
        /**
         * UserRole
         * @enum {string}
         */
        UserRole: "member" | "librarian" | "administrator";
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** WaiverRequest */
        WaiverRequest: {
            /** Reason */
            reason: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    bootstrap_api_v1_accounts_bootstrap_administrator_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrincipalResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deactivate_api_v1_accounts_deactivate_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeactivateAccountRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrincipalResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_librarian_api_v1_accounts_librarians_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrincipalResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    register_api_v1_accounts_register_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AccountRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrincipalResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    current_session_api_v1_auth_session_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResponse"];
                };
            };
        };
    };
    browse_api_v1_catalog_books_get: {
        parameters: {
            query?: {
                query?: string | null;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CatalogEntryResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_book_api_v1_catalog_books_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookRequestBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_book_api_v1_catalog_books__book_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                book_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CatalogEntryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_book_api_v1_catalog_books__book_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                book_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookRequestBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_copies_api_v1_catalog_books__book_id__copies_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
            };
            header?: never;
            path: {
                book_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookCopyResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_copy_api_v1_catalog_books__book_id__copies_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                book_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CopyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookCopyResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_copy_api_v1_catalog_copies__barcode__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                barcode: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CopyStatusRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookCopyResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    loans_api_v1_circulation_loans_get: {
        parameters: {
            query?: {
                username?: string | null;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoanViewResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    checkout_api_v1_circulation_loans_checkout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CheckoutRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoanViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    return_copy_api_v1_circulation_loans_return_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReturnRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoanViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    renew_api_v1_circulation_loans__loan_id__renew_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                loan_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoanViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reservations_api_v1_circulation_reservations_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReservationViewResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reserve_api_v1_circulation_reservations_books__book_id__post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                book_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReservationViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_api_v1_circulation_reservations__reservation_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                reservation_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReservationViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    book_requests_api_v1_engagement_book_requests_get: {
        parameters: {
            query?: {
                status?: components["schemas"]["RequestStatus"] | null;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookRequestViewResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_request_api_v1_engagement_book_requests_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AcquisitionRequestBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookRequestViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    acquire_request_api_v1_engagement_book_requests__request_id__acquire_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AcquiredRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookRequestViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_request_api_v1_engagement_book_requests__request_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookRequestViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    feedback_api_v1_engagement_feedback_get: {
        parameters: {
            query?: {
                status?: components["schemas"]["FeedbackStatus"] | null;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackViewResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_feedback_api_v1_engagement_feedback_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeedbackRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_feedback_api_v1_engagement_feedback__feedback_id__archive_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feedback_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_feedback_api_v1_engagement_feedback__feedback_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feedback_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedbackViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    fines_api_v1_finance_fines_get: {
        parameters: {
            query?: {
                username?: string | null;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FineViewResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    assess_api_v1_finance_fines_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ManualFineRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FineViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    fine_api_v1_finance_fines__fine_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                fine_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FineViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pay_api_v1_finance_fines__fine_id__payment_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                fine_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FineViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    waive_api_v1_finance_fines__fine_id__waiver_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                fine_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WaiverRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FineViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    operations_api_v1_insights_operations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OperationalReportResponse"];
                };
            };
        };
    };
    popular_api_v1_insights_popular_get: {
        parameters: {
            query?: {
                limit?: number | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PopularBookResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recommendations_api_v1_insights_recommendations_get: {
        parameters: {
            query?: {
                limit?: number | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecommendationResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    liveness_health_live_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    readiness_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
}
