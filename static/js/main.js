document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("plan-form");
    const queryInput = document.getElementById("user-query");
    const submitBtn = document.getElementById("submit-btn");
    const stepper = document.getElementById("status-stepper");
    const resultsSection = document.getElementById("results-section");
    const copyBtn = document.getElementById("copy-btn");

    const stepFlight = document.getElementById("step-flight");
    const stepHotel = document.getElementById("step-hotel");
    const stepItinerary = document.getElementById("step-itinerary");
    const stepFinal = document.getElementById("step-final");

    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    const tabSummary = document.getElementById("tab-summary");
    const tabFlights = document.getElementById("tab-flights");
    const tabHotels = document.getElementById("tab-hotels");
    const tabItinerary = document.getElementById("tab-itinerary");
    const metaThreadId = document.getElementById("meta-thread-id");
    const metaLlmCalls = document.getElementById("meta-llm-calls");

    let currentResponseData = null;

    // Example Chips handler
    document.querySelectorAll(".chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            queryInput.value = chip.getAttribute("data-query");
            queryInput.focus();
        });
    });

    // Tab Navigation
    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");

            tabBtns.forEach((b) => b.classList.remove("active"));
            tabPanes.forEach((p) => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
            }
        });
    });

    // Copy Plan to Clipboard
    copyBtn.addEventListener("click", async () => {
        if (!currentResponseData || !currentResponseData.answer) return;

        try {
            await navigator.clipboard.writeText(currentResponseData.answer);
            const originalText = copyBtn.innerText;
            copyBtn.innerText = "✅ Copied!";
            setTimeout(() => {
                copyBtn.innerText = originalText;
            }, 2000);
        } catch (err) {
            console.error("Failed to copy text", err);
        }
    });

    // Stepper progressive animation helper
    let stepInterval = null;
    const startStepper = () => {
        stepper.classList.remove("hidden");
        const steps = [stepFlight, stepHotel, stepItinerary, stepFinal];
        steps.forEach((s) => {
            s.className = "step-indicator";
        });

        let currentIdx = 0;
        steps[0].classList.add("active");

        stepInterval = setInterval(() => {
            if (currentIdx < steps.length - 1) {
                steps[currentIdx].classList.remove("active");
                steps[currentIdx].classList.add("done");
                currentIdx++;
                steps[currentIdx].classList.add("active");
            }
        }, 3500);
    };

    const stopStepper = () => {
        if (stepInterval) clearInterval(stepInterval);
        const steps = [stepFlight, stepHotel, stepItinerary, stepFinal];
        steps.forEach((s) => {
            s.className = "step-indicator done";
        });
    };

    // Form Submit Handler
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userQuery = queryInput.value.trim();
        if (!userQuery) return;

        submitBtn.disabled = true;
        submitBtn.querySelector(".btn-text").innerText = "Planning Travel...";
        resultsSection.classList.add("hidden");
        startStepper();

        try {
            const response = await fetch("/api/plan", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ user_input: userQuery }),
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Travel planning service failed.");
            }

            const data = await response.json();
            currentResponseData = data;
            stopStepper();

            // Render Markdown
            tabSummary.innerHTML = marked.parse(data.answer || "No response received.");
            tabFlights.innerHTML = marked.parse(data.flight_results || "No flight records retrieved.");
            tabHotels.innerHTML = marked.parse(data.hotel_results || "No hotel options retrieved.");
            tabItinerary.innerHTML = marked.parse(data.itinerary || "No preliminary itinerary generated.");

            metaThreadId.innerText = data.thread_id || "N/A";
            metaLlmCalls.innerText = data.llm_calls || 0;

            stepper.classList.add("hidden");
            resultsSection.classList.remove("hidden");
            resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

        } catch (error) {
            stopStepper();
            stepper.classList.add("hidden");
            alert(`Error: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            submitBtn.querySelector(".btn-text").innerText = "Generate Trip Plan";
        }
    });
});
