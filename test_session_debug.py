"""
Debug script to test session storage and retrieval
"""

from app import create_app


def test_session_flow():
    """Test the full session flow from simulation to results"""
    app = create_app()

    with app.test_client() as client:
        print("\n=== Testing Session Flow ===\n")

        # Step 1: Run simulation
        print("1. Running simulation (POST /run)...")
        response = client.post("/run", data={"run_simulation": "1"})
        print(f"   Status: {response.status_code}")
        print(
            f"   Redirect location: {response.location if response.status_code == 302 else 'N/A'}"
        )

        # Step 2: Check session after simulation
        with client.session_transaction() as sess:
            print("\n2. Session contents after simulation:")
            print(
                f"   - first_results_data: {sess.get('first_results_data') is not None}"
            )
            if sess.get("first_results_data"):
                print(f"     Type: {type(sess.get('first_results_data'))}")
                print(f"     Length: {len(sess.get('first_results_data'))}")
                print(
                    f"     Sample: {sess.get('first_results_data')[0] if sess.get('first_results_data') else 'N/A'}"
                )

            print(f"   - first_results_columns: {sess.get('first_results_columns')}")
            print(
                f"   - success_percentage: {sess.get('success_percentage')} (type: {type(sess.get('success_percentage'))})"
            )
            print(
                f"   - simulation_history: {len(sess.get('simulation_history', []))} entries"
            )

        # Step 3: View results
        print("\n3. Viewing results (GET /results)...")
        response = client.get("/results")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.data.decode("utf-8")
            print(
                f"   Contains 'No Results Available': {'No Results Available' in data}"
            )
            print(f"   Contains 'Success Rate': {'Success Rate' in data}")
            print(f"   Contains 'plotly': {'plotly' in data.lower()}")
            print(f"   Response length: {len(data)} bytes")
        else:
            print(f"   ERROR: {response.data.decode('utf-8')[:500]}")

        # Step 4: Check session after viewing results
        with client.session_transaction() as sess:
            print("\n4. Session contents after viewing results:")
            print(
                f"   - first_results_data: {sess.get('first_results_data') is not None}"
            )
            print(
                f"   - first_results_columns: {sess.get('first_results_columns') is not None}"
            )
            print(f"   - success_percentage: {sess.get('success_percentage')}")


if __name__ == "__main__":
    test_session_flow()
