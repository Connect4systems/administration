// Copyright (c) 2026, Connect 4 Systems and contributors
// For license information, please see license.txt

const build_default_terms = (doc) => [
	[
		"Article One - Preamble",
		"التمهيد",
		"The preamble and the information recorded in this contract form an integral part of this agreement.",
		"يعتبر التمهيد والبيانات الواردة في هذا العقد جزءاً لا يتجزأ منه ومكملاً ومفسراً لشروطه.",
	],
	[
		"Article Two - Purpose of Lease",
		"الغرض من الإيجار",
		`The Second Party leases unit ${doc.flat_no || ""} to the First Party for accommodation of the company's employees.`,
		`يؤجر الطرف الثاني الوحدة رقم ${doc.flat_no || ""} للطرف الأول بغرض استخدامها كسكن خاص بالعاملين لدى الشركة.`,
	],
	[
		"Article Three - Furnishings and Contents",
		"المنقولات والمحتويات",
		`The leased unit has a total area of ${doc.total_flat_area || ""} square meters and contains ${doc.no_of_rooms || ""} rooms. The parties shall record its contents in the attached contents table.`,
		`تبلغ مساحة العين المؤجرة ${doc.total_flat_area || ""} متراً مربعاً وتحتوي على عدد ${doc.no_of_rooms || ""} غرفة، ويتم تسجيل محتوياتها في جدول المحتويات المرفق.`,
	],
	[
		"Article Four - Lease Term",
		"مدة الإيجار",
		`The lease starts on ${doc.contract_start_date || ""} and ends on ${doc.contract_end_date || ""}. Any renewal shall be agreed in a new written contract.`,
		`تبدأ مدة الإيجار في ${doc.contract_start_date || ""} وتنتهي في ${doc.contract_end_date || ""}، وأي تجديد يكون بموجب عقد كتابي جديد.`,
	],
	[
		"Article Five - Rent and Payment Terms",
		"القيمة الإيجارية وطريقة السداد",
		`The rent is ${doc.monthly_rent || ""} per month, payable on a ${doc.payment_cycle || "monthly"} basis according to the agreed bank details.`,
		`تبلغ القيمة الإيجارية ${doc.monthly_rent || ""} شهرياً، وتسدد وفق دورة السداد ${doc.payment_cycle || "شهرياً"} طبقاً للبيانات البنكية المتفق عليها.`,
	],
	[
		"Article Six - Rental Property Deposit",
		"التأمين والوديعة التأمينية",
		`The insurance amount is ${doc.insurance || ""} and the security deposit is ${doc.deposit || ""}. Both shall be settled after handover, subject to lawful deductions.`,
		`تبلغ قيمة التأمين ${doc.insurance || ""} والوديعة التأمينية ${doc.deposit || ""}، ويتم تسويتهما بعد التسليم مع خصم أي مبالغ مستحقة قانوناً.`,
	],
	[
		"Article Seven - Delay in Rent Payment",
		"التأخير في دفع الإيجار",
		"Rent shall be paid within the agreed period. Delay shall be handled by written notice and according to the applicable law.",
		"تسدد القيمة الإيجارية خلال المدة المتفق عليها، ويتم التعامل مع التأخير بموجب إخطار كتابي ووفقاً للقانون واجب التطبيق.",
	],
	[
		"Article Eight - Subletting or Assignment",
		"التنازل أو التأجير من الباطن",
		"The First Party shall not sublet or assign the leased premises without the prior written consent of the Second Party.",
		"لا يجوز للطرف الأول التأجير من الباطن أو التنازل عن العين المؤجرة إلا بعد الحصول على موافقة كتابية مسبقة من الطرف الثاني.",
	],
	[
		"Article Nine - Inspection",
		"المعاينة",
		"The First Party acknowledges that it has inspected the leased premises and accepted them in their current condition.",
		"يقر الطرف الأول بأنه عاين العين المؤجرة وقبلها بالحالة التي هي عليها وقت التعاقد.",
	],
	[
		"Article Ten - Handover of the Leased Premises",
		"تسليم العين المؤجرة",
		`The First Party shall receive the leased premises on ${doc.contract_start_date || ""} for the purpose stated in this agreement.`,
		`يتسلم الطرف الأول العين المؤجرة بتاريخ ${doc.contract_start_date || ""} للغرض المبين في هذا العقد.`,
	],
	[
		"Article Eleven - Renovations",
		"الترميمات",
		"No internal modification or renovation may be made without the prior written approval of the Second Party.",
		"لا يجوز إجراء أي تعديل أو ترميم داخلي إلا بعد الحصول على موافقة كتابية مسبقة من الطرف الثاني.",
	],
	[
		"Article Twelve - Early Termination / Vacating Premises",
		"الإخلاء قبل الميعاد / الإنهاء المبكر",
		"Early termination and vacating shall require written notice and settlement of all amounts due under this contract.",
		"يتطلب الإنهاء المبكر وإخلاء المكان توجيه إخطار كتابي وتسوية جميع المبالغ المستحقة بموجب هذا العقد.",
	],
	[
		"Article Thirteen - Jurisdiction",
		"الاختصاص القضائي",
		"The competent courts shall have jurisdiction over any dispute arising from the interpretation or execution of this contract.",
		"تختص المحاكم المختصة بنظر أي نزاع ينشأ عن تفسير أو تنفيذ هذا العقد.",
	],
	[
		"Article Fourteen - Chosen Domicile",
		"الموطن المختار",
		"The addresses stated for the parties shall be their chosen domiciles for notices and official correspondence.",
		"يقر الطرفان بأن العناوين المبينة لكل منهما هي الموطن المختار للمراسلات والإخطارات الرسمية.",
	],
	[
		"Article Fifteen - Contract Copies",
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

		frm.add_custom_button(__("Create Flat"), () => {
			frappe.call({
				method: "administration.administration.doctype.flat.flat.make_flat",
				args: { source_doctype: frm.doc.doctype, source_name: frm.doc.name },
				freeze: true,
				callback(r) {
					if (r.message) {
						const flat = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", "Flat", flat.name);
					}
				},
			});
		});

		frm.add_custom_button(__("Create Flat Contract"), async () => {
			const supplier_name =
				frm.doc.flat_owner_name ||
				(
					await frappe.db.get_value("Supplier", frm.doc.flat_owner, "supplier_name")
				).message?.supplier_name ||
				"";

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
				contract.flat_rent_request = frm.doc.flat_rent_request || "";
				contract.first_party_name = "CSCEC International Egypt for Construction Company Co., LTD s.s.c";
				contract.first_party_address = "3rd Floor, The NOX Mall, Third Sector, North 90th Street, Fifth Settlement, New Cairo, Cairo";
				contract.first_party_representative = "Authorized Manager";
				contract.second_party_name = supplier_name;
				contract.second_party_name_arabic = frm.doc.legal_name || "";
				contract.second_party_id = frm.doc.owner_id || "";
				contract.attach_id = frm.doc.attach_id || "";
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
