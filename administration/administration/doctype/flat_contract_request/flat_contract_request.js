// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

const build_default_terms = (doc) => [
	[
		"Preamble",
		"التمهيد",
		"The preamble and the information recorded in this contract form an integral part of this agreement.",
		"يعتبر التمهيد والبيانات الواردة في هذا العقد جزءاً لا يتجزأ منه ومكملاً ومفسراً لشروطه.",
	],
	[
		"Purpose of Lease",
		"الغرض من الإيجار",
		`The Second Party leases unit ${doc.flat_no || ""} to the First Party for accommodation of the company's employees.`,
		`يؤجر الطرف الثاني الوحدة رقم ${doc.flat_no || ""} للطرف الأول بغرض استخدامها كسكن خاص بالعاملين لدى الشركة.`,
	],
	[
		"Leased Unit Details",
		"بيانات العين المؤجرة",
		`The leased unit has a total area of ${doc.total_flat_area || ""} square meters and contains ${doc.no_of_rooms || ""} rooms.`,
		`تبلغ مساحة العين المؤجرة ${doc.total_flat_area || ""} متراً مربعاً وتحتوي على عدد ${doc.no_of_rooms || ""} غرفة.`,
	],
	[
		"Rent and Payment Terms",
		"القيمة الإيجارية وطريقة السداد",
		`The rent is ${doc.monthly_rent || ""} per month, payable on a ${doc.payment_cycle || "monthly"} basis according to the agreed bank details.`,
		`تبلغ القيمة الإيجارية ${doc.monthly_rent || ""} شهرياً، وتسدد وفق دورة السداد ${doc.payment_cycle || "شهرياً"} طبقاً للبيانات البنكية المتفق عليها.`,
	],
	[
		"Insurance",
		"التأمين",
		`The insurance amount is ${doc.insurance || ""} and shall be settled according to the terms of this contract.`,
		`تبلغ قيمة التأمين ${doc.insurance || ""} ويتم تسويته وفقاً لشروط هذا العقد.`,
	],
	[
		"Security Deposit",
		"الوديعة التأمينية",
		`The security deposit is ${doc.deposit || ""} and shall be returned after handover, subject to lawful deductions.`,
		`تبلغ الوديعة التأمينية ${doc.deposit || ""} وترد بعد التسليم مع خصم أي مبالغ مستحقة قانوناً.`,
	],
	[
		"Furnishings and Contents",
		"المنقولات والمحتويات",
		"The parties shall record the condition and contents of the leased premises in the contents table attached to this contract.",
		"يتفق الطرفان على تسجيل حالة ومحتويات العين المؤجرة في جدول المحتويات المرفق بهذا العقد.",
	],
	[
		"Lease Term",
		"مدة الإيجار",
		`The lease starts on ${doc.contract_start_date || ""} and ends on ${doc.contract_end_date || ""}. Any renewal shall be agreed in a new written contract.`,
		`تبدأ مدة الإيجار في ${doc.contract_start_date || ""} وتنتهي في ${doc.contract_end_date || ""}، وأي تجديد يكون بموجب عقد كتابي جديد.`,
	],
	[
		"Handover and Maintenance",
		"التسليم والصيانة",
		"The First Party shall inspect and receive the leased premises in its recorded condition and maintain it with reasonable care.",
		"يقر الطرف الأول بأنه عاين العين المؤجرة وتسلمها بالحالة الموضحة ويلتزم بالمحافظة عليها بعناية.",
	],
	[
		"Termination and Jurisdiction",
		"الإنهاء والاختصاص",
		"Termination, notices, and disputes shall be handled according to applicable laws and the written terms of this agreement.",
		"يتم إنهاء العقد وتوجيه الإخطارات وتسوية المنازعات وفقاً للقوانين واجبة التطبيق والشروط المكتوبة في هذا العقد.",
	],
	[
		"Contract Copies",
		"نسخ العقد",
		"This contract is made in two original copies, one for each party.",
		"حرر هذا العقد من نسختين أصليتين، يحتفظ كل طرف بنسخة للعمل بموجبها عند اللزوم.",
	],
];

frappe.ui.form.on("Flat Contract Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		frm.add_custom_button(__("Create Flat Contract"), () => {
			frappe.model.with_doctype("Flat Contract", () => {
				const contract = frappe.model.get_new_doc("Flat Contract");
				const copied_fields = [
					"project",
					"date",
					"contract_start_date",
					"contract_end_date",
					"flat_owner",
					"owner_id",
					"attach_id",
					"governorate",
					"city",
					"area",
					"address",
					"flat_no",
					"floor_no",
					"total_flat_area",
					"no_of_rooms",
					"no_of_beds",
					"no_of_ketchen_room",
					"no_of_bathroom",
					"monthly_rent",
					"payment_cycle",
					"deposit",
					"insurance",
					"bank",
					"iban",
					"ownership_documentation",
					"notes",
				];

				copied_fields.forEach((fieldname) => {
					contract[fieldname] = frm.doc[fieldname];
				});

				contract.flat_contract_request = frm.doc.name;
				contract.first_party_name = "CSCEC International Egypt for Construction Company Co., LTD s.s.c";
				contract.first_party_address = "3rd Floor, The NOX Mall, Third Sector, North 90th Street, Fifth Settlement, New Cairo, Cairo";
				contract.first_party_representative = "Authorized Manager";
				contract.second_party_name = frm.doc.flat_owner || "";
				contract.second_party_id = frm.doc.owner_id || "";
				build_default_terms(frm.doc).forEach((term, index) => {
					const contract_term = frappe.model.add_child(contract, "Flat Contract Term", "terms");
					contract_term.term_no = index + 1;
					contract_term.english_term = `${term[0]}\n${term[2]}`;
					contract_term.arabic_term = `${term[1]}\n${term[3]}`;
				});

				(frm.doc.flat_contents || []).forEach((row) => {
					const content = frappe.model.add_child(contract, "Flat Contents", "flat_contents");
					["item_name", "description", "qty", "image"].forEach((fieldname) => {
						content[fieldname] = row[fieldname];
					});
				});

				frappe.model.sync(contract);
				frappe.set_route("Form", "Flat Contract", contract.name);
			});
		});
	},
});
