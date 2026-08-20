def seed(
    *,
    initialize_schema: bool = True,
    reset_existing: bool = True,
    clean_fixtures: bool = True,
):
    settings = get_settings()
    environment = settings.app_env.upper()

    # No synthetic seed path is permitted in production,
    # even if a caller tries to bypass init_db manually.
    if environment == "PROD":
        raise RuntimeError(
            "Synthetic seed execution is "
            "forbidden in PROD."
        )

    # Azure preprod has exactly one permitted seed mode:
    # migrated + empty DB + non-destructive synthetic bootstrap.
    if environment == "AZURE-PREPROD":
        if not settings.synthetic_only:
            raise RuntimeError(
                "AZURE-PREPROD synthetic seed "
                "requires SYNTHETIC_ONLY=true."
            )

        if settings.real_data_allowed:
            raise RuntimeError(
                "AZURE-PREPROD synthetic seed "
                "requires REAL_DATA_ALLOWED=false."
            )

        if initialize_schema:
            raise RuntimeError(
                "AZURE-PREPROD synthetic seed "
                "requires initialize_schema=False."
            )

        if reset_existing:
            raise RuntimeError(
                "AZURE-PREPROD synthetic seed "
                "requires reset_existing=False."
            )

        if clean_fixtures:
            raise RuntimeError(
                "AZURE-PREPROD synthetic seed "
                "requires clean_fixtures=False."
            )

    elif not reset_existing:
        raise RuntimeError(
            "Non-destructive synthetic seed mode "
            "is restricted to AZURE-PREPROD."
        )

    if initialize_schema:
        init_db()

    with SessionLocal() as db:
        if reset_existing:
            db.execute(
                update(
                    EngineeringReview
                ).values(
                    current_scope_id=None
                )
            )

            db.execute(
                update(
                    Invoice
                ).values(
                    requirement_decision_id=None
                )
            )

        reset_order = [
            # Shared-domain foundation records are reset before their
            # canonical master-content/project parents in disposable TEST.
            SignaturePacket,
            FormSignatureRequirement,
            FormMappingReleaseQAGate,
            AutomationReadinessAssessment,
            FormQARun,
            FormValidationResult,
            GeneratedArtifact,
            FormInstance,
            FormMappingRule,
            FormMappingRelease,
            SemanticValueAssertion,
            SemanticKeyDefinition,
            FormAutomationProfile,
            MasterContentApplicability,
            TechnicalRuleEvaluation,
            TechnicalRuleLineage,
            TechnicalRule,
            TechnicalRuleSetVersion,
            RequirementDecision,
            RequirementEvidenceEvaluation,
            RequirementEvaluation,
            RequirementApplicabilityDecision,
            RequirementPolicyLineage,
            RequirementEvidenceConstraint,
            RequirementPolicyItem,
            RequirementGroup,
            RequirementPolicyVersion,
            RequirementDefinition,
            AuthorityOutcome,
            ExternalInteractionProfile,
            AuthorityCaseWorkPeriod,
            AuthorityCaseIdentifier,
            AuthorityCase,
            RegulatoryJourney,
            RegulatoryLifecyclePhase,
            ServiceTypeVersion,
            ServiceType,
            ExternalBodyUnit,
            ExternalBody,
            Jurisdiction,
            *EXPANSION_RESET_MODELS,
            ProductionModeDecision,
            G10EvidenceItem,
            RoleReadinessMatrix,
            PilotWorkflowApproval,
            ShadowDefectDisposition,
            AcceptanceMetric,
            AcceptanceRehearsalRun,
            RoleTrainingChecklist,
            KillSwitchReadiness,
            RestoreRehearsal,
            RecoveryManifest,
            IncidentImpactAssessment,
            WorkflowSafetyHold,
            IntegrityIncident,
            SupportCase,
            FindingPreventionControl,
            PriorFindingPreventiveCheck,
            FindingRecurrenceAnalysisItem,
            FindingRecurrenceAnalysisRun,
            HumanTakeoverEvent,
            MfaChallengeEvent,
            AttendedAuthSession,
            TargetRenderingCoverage,
            VariantCompatibilityResult,
            ScenarioVariant,
            OperatorTaskTiming,
            NotificationDeliveryAttempt,
            ExternalMutationObservation,
            HumanMonitoringCapture,
            AuthorityStateComparison,
            MonitoringStateSnapshot,
            AuthorityCommentObservation,
            AuthorityStatusObservation,
            PortalContractValidationRun,
            PortalDriftEvent,
            PortalReadContract,
            MonitoringCheck,
            MonitoringExecutionDecision,
            MonitoringRun,
            MonitoringPolicy,
            GridFieldDiff,
            GridRowReconciliationResult,
            GridReconciliationRun,
            GridPersistenceEvidence,
            PortalGridRowObservation,
            PortalDerivedFieldReconciliation,
            PortalStructureFingerprint,
            AttachmentReconciliationResult,
            AttachmentPersistenceEvidence,
            AttachmentAssociationIntent,
            AttachmentManifestItem,
            AttachmentCategoryRule,
            FieldMatrixCoverage,
            RequirementMatrixCoverage,
            RuleCandidate,
            ControlRun,
            ControlDefinition,
            ResubmissionReadinessEvaluation,
            ApprovalApplicabilityEvaluation,
            SubmittedSnapshot,
            PrecheckClearanceEvaluation,
            FindingHistoryLink,
            FindingReopenEvent,
            FindingDispute,
            FindingClosureEvaluation,
            FindingResolutionEvidence,
            FindingResolution,
            CorpusCaseResult,
            CorpusCase,
            CorpusRun,
            ShadowCorrection,
            StaleReason,
            MaterialChangeEvent,
            LineageEdge,
            ConfigurationChangeImpactPolicy,
            AuthorityApprovalValidity,
            DocumentValidity,
            NotificationReadState,
            NotificationEvent,
            WorkflowTask,
            Finding,
            AuthorityEvent,
            SubmissionCycle,
            PortalValidationFindingRule,
            FindingRoutingRule,
            FindingSlaPolicy,
            FindingCode,
            OperatorExerciseEvidence,
            SubmissionConfirmation,
            MunicipalityPreparationException,
            SubmissionHandoff,
            AttendedSession,
            AuthorityPrecheckItem,
            AuthorityPrecheckRun,
            HumanPortalVerification,
            PortalReconciliationResult,
            PortalSnapshot,
            PortalIntendedState,
            PortalGridRowIntent,
            PreparationSnapshot,
            PreparationRevision,
            Approval,
            ExcelProjection,
            RenderedForm,
            FormTemplateVersion,
            FormTemplate,
            AttachmentManifest,
            PackageItem,
            Package,
            ReadinessResultItem,
            PackageReadinessEvaluation,
            MinimumPackageDefinition,
            OfficeCredential,
            ProfessionalCredential,
            ApplicableRuleSet,
            ConfigurationBundle,
            ConfigurationArtifact,
            AuditEvent,
            StorageOutboxEvent,
            StorageOperation,
            SignoffCProposal,
            Stage2ReviewAcknowledgement,
            Stage2Baseline,
            DeliveryAuthorityStatus,
            Phase0Decision,
            PilotCohort,
            PrecheckDecision,
            MunicipalityOperationDecision,
            DeliveryScenario,
            BusinessKpiTarget,
            BusinessBaseline,
            Tier2BacklogItem,
            Tier1Decision,
            AcceptanceCorpusDefinition,
            ThresholdDefinition,
            AdjudicationHistory,
            AdjudicationCase,
            PhaseBaseline,
            Representation,
            Authorization,
            PropertyOwnership,
            ExcelProjectionRule,
            ExcelProjectRow,
            SynologyProjectBootstrap,
            ProjectNumberReservation,
            ProjectInitiation,
            TargetRenderingRule,
            Party,
            Property,
            LegacyFixtureAlias,
            SyntheticFixtureSet,
            SpikeFieldResult,
            SpikeDocumentResult,
            ExtractionSpikeRun,
            GoldFieldLabel,
            GoldDocumentLabel,
            RealDocumentTestGate,
            MunicipalityDraft,
            MunicipalityConfig,
            Conflict,
            DrawingMetadataControl,
            AttachmentCategoryConfig,
            ApprovalDependency,
            RequirementConfig,
            FieldAuthorityRule,
            VerifiedAssertion,
            FieldObservation,
            DocumentClassification,
            DocumentVersion,
            Document,
            FieldDefinition,
            ScenarioConfig,
            ExternalSystemLink,
            PermitApplication,
            Project,
            User,
            ConsultancyOffice,
            DiscoveryDecision,
            BusinessCase,
            VolumeBaseline,
            MinistryInquiry,
            RaidItem,
        ]

        # PostgreSQL enforces the complete FK graph while SQLite's reset
        # path historically relied on the hand-maintained model order.
        # Disposable local TEST databases may be reset atomically.
        # Azure preprod never takes this branch.
        if reset_existing:
            if (
                db.bind.dialect.name
                == "postgresql"
                and environment == "TEST"
                and settings.synthetic_only
                and not os.getenv("VERCEL")
            ):
                tables = ", ".join(
                    f'"{name}"'
                    for name
                    in Base.metadata.tables
                )

                db.execute(
                    text(
                        f"TRUNCATE TABLE {tables} "
                        "RESTART IDENTITY CASCADE"
                    )
                )

            else:
                for model in reset_order:
                    db.execute(
                        delete(model)
                    )

        else:
            # Azure bootstrap may populate only a completely empty,
            # already-migrated application database.
            occupied_tables = []

            for table in Base.metadata.sorted_tables:
                if (
                    db.execute(
                        select(table).limit(1)
                    ).first()
                    is not None
                ):
                    occupied_tables.append(
                        table.name
                    )

            if occupied_tables:
                raise RuntimeError(
                    "Non-destructive synthetic seed "
                    "requires an empty migrated "
                    "database; existing application "
                    "data was found."
                )

        office = ConsultancyOffice(
            office_code="QEC-DOHA",
            name_en="AMEC Engineering",
            name_ar=(
                "مكتب آفاق الخليج "
                "للاستشارات الهندسية"
            ),
            status="ACTIVE",
        )

        db.add(office)
        db.flush()

        users = [
            (
                "owner@amec.synthetic",
                "Maha Al-Khatri",
                Role.OWNER_SPONSOR,
            ),
            (
                "champion@amec.synthetic",
                "Yousef Nasser",
                Role.PROCESS_CHAMPION,
            ),
            (
                "steward@amec.synthetic",
                "Noura Salem",
                Role.REQUIREMENT_STEWARD,
            ),
            (
                "engineer@amec.synthetic",
                "Omar Haddad",
                Role.RESPONSIBLE_ENGINEER,
            ),
            (
                "preparer@amec.synthetic",
                "Rana Faisal",
                Role.PERMIT_PREPARER,
            ),
            (
                "submitter@amec.synthetic",
                "Khalid Mansour",
                Role.FINAL_SUBMITTER,
            ),
            (
                "admin@amec.synthetic",
                "Samir Qasem",
                Role.SYSTEM_ADMIN,
            ),
        ]

        db.add_all(
            [
                User(
                    email=email,
                    display_name=name,
                    role=role,
                    office_id=office.id,
                )
                for email, name, role
                in users
            ]
        )

        db.flush()

        projects = [
            Project(
                project_number=(
                    CANONICAL_PROJECT_IDS[0]
                ),
                project_name="Al Noor Villa",
                office_id=office.id,
                workstream="RESIDENTIAL",
                status="ACTIVE",
                municipality="Doha",
                permit_type="Building Permit",
                assigned_engineer="Omar Haddad",
            ),
            Project(
                project_number=(
                    CANONICAL_PROJECT_IDS[1]
                ),
                project_name=(
                    "West Bay Residence"
                ),
                office_id=office.id,
                workstream="RESIDENTIAL",
                status="ACTIVE",
                municipality="Doha",
                permit_type="Building Permit",
                assigned_engineer="Rana Faisal",
            ),
            Project(
                project_number=(
                    CANONICAL_PROJECT_IDS[2]
                ),
                project_name=(
                    "Lusail Office Annex"
                ),
                office_id=office.id,
                workstream="COMMERCIAL",
                status="ACTIVE",
                municipality="Lusail",
                permit_type="Fit-out Permit",
                assigned_engineer="Omar Haddad",
            ),
            Project(
                project_number=(
                    CANONICAL_PROJECT_IDS[3]
                ),
                project_name=(
                    "Pearl Community Clinic"
                ),
                office_id=office.id,
                workstream="COMMERCIAL",
                status="ON_HOLD",
                municipality="Doha",
                permit_type="Renovation Permit",
                assigned_engineer="Noura Salem",
            ),
        ]

        db.add_all(projects)
        db.flush()

        apps = [
            PermitApplication(
                project_id=projects[0].id,
                authority=(
                    "Permit Authority Simulator"
                ),
                municipality="Doha",
                permit_type="Building Permit",
                external_request_number=(
                    CANONICAL_APPLICATION_IDS[0]
                ),
                application_status=(
                    ApplicationStatus.DRAFT
                ),
                repetition_count=0,
            ),
            PermitApplication(
                project_id=projects[1].id,
                authority=(
                    "Permit Authority Simulator"
                ),
                municipality="Doha",
                permit_type="Building Permit",
                external_request_number=(
                    CANONICAL_APPLICATION_IDS[1]
                ),
                application_status=(
                    ApplicationStatus.RETURNED
                ),
                repetition_count=2,
            ),
            PermitApplication(
                project_id=projects[2].id,
                authority=(
                    "Permit Authority Simulator"
                ),
                municipality="Lusail",
                permit_type="Fit-out Permit",
                external_request_number=(
                    CANONICAL_APPLICATION_IDS[2]
                ),
                application_status=(
                    ApplicationStatus
                    .UNDER_REVIEW
                ),
                repetition_count=1,
            ),
            PermitApplication(
                project_id=projects[3].id,
                authority=(
                    "Permit Authority Simulator"
                ),
                municipality="Doha",
                permit_type=(
                    "Renovation Permit"
                ),
                external_request_number=(
                    CANONICAL_APPLICATION_IDS[3]
                ),
                application_status=(
                    ApplicationStatus.APPROVED
                ),
                repetition_count=1,
            ),
        ]

        db.add_all(apps)
        db.flush()

        external_links = [
            (
                projects[0],
                apps[0],
                (
                    f"2026/"
                    f"{CANONICAL_PROJECT_IDS[0]}"
                    "_Al-Noor-Villa"
                ),
                2,
            ),
            (
                projects[1],
                apps[1],
                (
                    f"2026/"
                    f"{CANONICAL_PROJECT_IDS[1]}"
                    "_West-Bay-Residence"
                ),
                3,
            ),
            (
                projects[2],
                apps[2],
                (
                    f"2026/"
                    f"{CANONICAL_PROJECT_IDS[2]}"
                    "_Lusail-Office-Annex"
                ),
                4,
            ),
            (
                projects[3],
                apps[3],
                (
                    f"2026/"
                    f"{CANONICAL_PROJECT_IDS[3]}"
                    "_Pearl-Community-Clinic"
                ),
                5,
            ),
        ]

        for (
            project,
            application,
            root,
            row,
        ) in external_links:
            db.add_all(
                [
                    ExternalSystemLink(
                        project_id=project.id,
                        system_type=(
                            SystemType.SYNOLOGY
                        ),
                        external_reference=root,
                        display_reference=root,
                        metadata_json={
                            "synthetic": True
                        },
                    ),
                    ExternalSystemLink(
                        project_id=project.id,
                        system_type=(
                            SystemType.EXCEL
                        ),
                        external_reference=(
                            "GENERAL FOLLOW UP "
                            f"/ row {row}"
                        ),
                        display_reference=(
                            "GENERAL FOLLOW UP "
                            f"/ row {row}"
                        ),
                        metadata_json={
                            "synthetic": True
                        },
                    ),
                    ExternalSystemLink(
                        project_id=project.id,
                        system_type=(
                            SystemType.MUNICIPALITY
                        ),
                        external_reference=(
                            application
                            .external_request_number
                        ),
                        display_reference=(
                            "Permit Authority "
                            "Simulator / "
                            f"{application.external_request_number}"
                        ),
                        metadata_json={
                            "synthetic": True
                        },
                    ),
                ]
            )

        decisions = [
            (
                "PRIVACY",
                "third_party_processing",
                DecisionStatus.UNKNOWN,
                (
                    "Can PermitOps process "
                    "QIDs/title deeds?"
                ),
            ),
            (
                "DATA_LOCATION",
                "approved_data_location",
                DecisionStatus.UNKNOWN,
                (
                    "Which approved environment "
                    "may hold test real documents?"
                ),
            ),
            (
                "AI_EGRESS",
                "external_ai_route",
                DecisionStatus.BLOCKED,
                (
                    "External AI route disabled "
                    "until approved."
                ),
            ),
            (
                "DELIVERY_LOCATION",
                (
                    "approved_test_real_"
                    "document_location"
                ),
                DecisionStatus.UNKNOWN,
                (
                    "Approved TEST real-document "
                    "location."
                ),
            ),
            (
                "PORTAL_ACCESS",
                (
                    "preparer_submitter_"
                    "separation"
                ),
                DecisionStatus.UNKNOWN,
                (
                    "Can preparer and final "
                    "submitter roles be separated?"
                ),
            ),
            (
                "BUSINESS_PROCESS",
                "assisted_entry_baseline",
                DecisionStatus.PROVISIONAL,
                (
                    "Assisted entry is the MVP "
                    "planning default."
                ),
            ),
            (
                "VOLUME",
                "applications_month",
                DecisionStatus.PROVISIONAL,
                (
                    "Synthetic volume input only."
                ),
            ),
            (
                "EXCEL",
                "excel_canonical_truth",
                DecisionStatus.CONFIRMED,
                (
                    "Excel is an external "
                    "representation, not canonical "
                    "truth."
                ),
            ),
            (
                "SYNOLOGY",
                "project_root_pattern",
                DecisionStatus.PROVISIONAL,
                (
                    "2026/PRJ-number_Name pattern "
                    "is a synthetic hypothesis."
                ),
            ),
            (
                "AUTHORITY",
                "api_availability",
                DecisionStatus.UNKNOWN,
                (
                    "Authority API availability "
                    "has not been confirmed."
                ),
            ),
        ]

        db.add_all(
            [
                DiscoveryDecision(
                    category=category,
                    key=key,
                    status=status,
                    value_json={
                        "synthetic": True
                    },
                    owner="TBD",
                    notes=notes,
                )
                for (
                    category,
                    key,
                    status,
                    notes,
                ) in decisions
            ]
        )

        db.add(
            BusinessCase(
                values_json=(
                    DEFAULT_BUSINESS_CASE
                )
            )
        )

        db.add(
            VolumeBaseline(
                values_json={
                    "applications_per_month": 25,
                    "active_permit_preparers": 3,
                    "average_open_applications": 18,
                    "peak_concurrent_applications": 8,
                    "portal_accounts": 3,
                    "sessions_per_day": 10,
                    "relogin_frequency": "UNKNOWN",
                    "excel_simultaneous_users": 4,
                }
            )
        )

        questions = [
            (
                "PREPARER_ROLE",
                (
                    "Can a user prepare a draft "
                    "without final-submission "
                    "authority?"
                ),
            ),
            (
                "SUBMITTER_SEPARATION",
                (
                    "Can another authorized user "
                    "submit a prepared draft?"
                ),
            ),
            (
                "SANDBOX",
                (
                    "Is a training/test "
                    "environment available?"
                ),
            ),
            (
                "STATUS_READ",
                (
                    "Is read-only application "
                    "status access available?"
                ),
            ),
            (
                "COMMENTS_READ",
                (
                    "Can comments/results be "
                    "exported/read electronically?"
                ),
            ),
            (
                "PRECHECK_RESULTS",
                (
                    "Can authority AI/precheck "
                    "results be exported or "
                    "accessed?"
                ),
            ),
            (
                "API",
                (
                    "Is a consultancy-facing "
                    "integration/API available "
                    "and what is the onboarding "
                    "process?"
                ),
            ),
        ]

        db.add_all(
            [
                MinistryInquiry(
                    question_code=code,
                    question=question,
                    status=(
                        InquiryStatus.NOT_ASKED
                    ),
                    client_owner="TBD",
                )
                for code, question
                in questions
            ]
        )

        raid = [
            (
                RaidType.RISK,
                (
                    "R1 - Client data processing "
                    "permissions unknown"
                ),
                (
                    "Real sensitive-document "
                    "processing approval is not "
                    "established."
                ),
                "HIGH",
                "TBD",
                (
                    "Synthetic only until "
                    "decision"
                ),
            ),
            (
                RaidType.RISK,
                (
                    "R2 - Ministry automation "
                    "permissions unknown"
                ),
                (
                    "Authority automation "
                    "boundaries are unknown."
                ),
                "HIGH",
                "TBD",
                "Use read-only simulator",
            ),
            (
                RaidType.ISSUE,
                (
                    "R3 - Real portal behavior "
                    "not yet mapped"
                ),
                (
                    "No official portal has "
                    "been contacted."
                ),
                "MEDIUM",
                "TBD",
                "Discovery inquiry",
            ),
            (
                RaidType.RISK,
                (
                    "R4 - Arabic OCR performance "
                    "unknown"
                ),
                "OCR is deferred.",
                "MEDIUM",
                "TBD",
                (
                    "Create synthetic acceptance "
                    "corpus later"
                ),
            ),
            (
                RaidType.ASSUMPTION,
                (
                    "R5 - Pilot project not yet "
                    "frozen"
                ),
                (
                    "No candidate is "
                    "automatically selected."
                ),
                "MEDIUM",
                "Client",
                "Review candidate list",
            ),
            (
                RaidType.ISSUE,
                (
                    "R6 - Excel locking behavior "
                    "not yet validated"
                ),
                (
                    "Workbook lock behavior is "
                    "simulated only."
                ),
                "MEDIUM",
                "TBD",
                "Validate with client",
            ),
            (
                RaidType.DEPENDENCY,
                (
                    "D1 - Responsible Engineer "
                    "availability required"
                ),
                (
                    "Pilot requires an available "
                    "responsible engineer."
                ),
                "MEDIUM",
                "Client",
                "Confirm availability",
            ),
            (
                RaidType.DEPENDENCY,
                (
                    "D2 - Client Ministry "
                    "inquiry required"
                ),
                (
                    "Narrow process questions "
                    "need client ownership."
                ),
                "HIGH",
                "Client",
                "Assign inquiry owner",
            ),
            (
                RaidType.DEPENDENCY,
                (
                    "D3 - Security/hosting "
                    "approval required"
                ),
                (
                    "Hosting and raw-data route "
                    "remain open."
                ),
                "HIGH",
                "Client",
                "Obtain approval",
            ),
            (
                RaidType.ASSUMPTION,
                (
                    "A1 - Assisted municipality "
                    "preparation is planning "
                    "default"
                ),
                (
                    "Human final submission "
                    "remains outside Week 1 "
                    "scope."
                ),
                "LOW",
                "Product",
                "Validate in Phase 0",
            ),
        ]

        db.add_all(
            [
                RaidItem(
                    type=raid_type,
                    title=title,
                    description=description,
                    severity=severity,
                    owner=owner,
                    status="OPEN",
                    mitigation=mitigation,
                    phase0_close_impact=(
                        "BLOCKER"
                        if title.startswith(
                            (
                                "R1",
                                "R5",
                                "D2",
                                "D3",
                            )
                        )
                        else (
                            "CONDITION"
                            if title.startswith(
                                (
                                    "R2",
                                    "R4",
                                    "D1",
                                    "A1",
                                )
                            )
                            else "NONE"
                        )
                    ),
                )
                for (
                    raid_type,
                    title,
                    description,
                    severity,
                    owner,
                    mitigation,
                ) in raid
            ]
        )

        seed_week2(
            db,
            projects,
        )
        seed_week3(
            db,
            projects,
        )
        seed_week4(
            db,
            projects,
        )
        seed_week45(
            db,
            projects,
        )
        seed_week7(
            db,
            projects,
        )
        seed_week8(
            db,
            projects,
        )
        seed_week9(
            db,
            projects,
        )
        seed_week10(
            db,
            projects,
        )
        seed_week11(
            db,
            projects,
        )
        seed_week12(
            db,
            projects,
        )
        seed_week13(
            db,
            projects,
        )
        seed_week14(
            db,
            projects,
        )
        seed_reconciliation(
            db,
            projects,
        )

        seed_users = db.scalars(
            select(User).order_by(
                User.email
            )
        ).all()

        seed_expansion(
            db,
            office,
            seed_users,
            projects,
            apps,
        )

        seed_persona_issues_notifications(
            db
        )

        for (
            project,
            application,
        ) in zip(
            projects,
            apps,
        ):
            ensure_project_sources_task(
                db,
                project,
                application,
            )

        db.commit()

    create_fixtures(
        synthetic_workspace_root(),
        clean=clean_fixtures,
    )

    ensure_primary_proposal_sources()
    ensure_proposals_contracts_demo_state()
    ensure_contract_center_golden_state()
