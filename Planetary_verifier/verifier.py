import ee
import os

# Initialize Earth Engine
# Run ee.Authenticate() in your terminal if you haven't yet
ee.Initialize(project='semiotic-art-483903-r6')

class PlanetaryVerifier:
    def __init__(self):
        self.collection_id = "COPERNICUS/S2_SR_HARMONIZED"

    def verify_zonal_truth(self, lat, lon, target_ndvi):
        if lat == "NOT_PROVIDED" or lon == "NOT_PROVIDED":
            return {
                "status": "DECLASSIFIED", 
                "reason": "Borrower failed to provide Project Site coordinates."
            }

        try:
            # 1. PARSE COORDINATES
            lat_f = float(str(lat).strip())
            lon_f = float(str(lon).strip())
            
            # 2. GEOSPATIAL POLYGON ALGORITHM (Spatial Truth)
            # We buffer the point to create a 1km x 1km square (Polygon)
            point = ee.Geometry.Point([lon_f, lat_f])
            roi = point.buffer(500).bounds()

            # PRINTING THE POLYGON FOR MANUAL VERIFICATION
            poly_coords = roi.coordinates().getInfo()
            print(f"\n🌐 GEOSPATIAL AUDIT BOX GENERATED:")
            print(f"Center: {lat_f}, {lon_f}")
            print(f"Polygon Corners: {poly_coords}")

            # 3. TEMPORAL MEDIAN STACKING (30-Day Window)
            # We look back 30 days from today to stack images and remove clouds
            end_date = '2026-01-01'
            start_date = '2025-09-01'

            s2_data = (ee.ImageCollection(self.collection_id)
                       .filterBounds(roi)
                       .filterDate(start_date, end_date)
                       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))

            if s2_data.size().getInfo() == 0:
                return {"status": "ERROR", "reason": "No clear satellite imagery found in the 30-day window."}
            
            image_count = s2_data.size().getInfo()

            if image_count == 0:
                return {"status": "ERROR", "reason": "No imagery found in 90-day window."}
                
            # 4. NDVI CALCULATION & MEDIAN REDUCTION
            def add_ndvi(img):
                return img.addBands(img.normalizedDifference(['B8', 'B4']).rename('NDVI'))

            # The .median() part handles the "Stacking" to find the statistical truth
            median_image = s2_data.map(add_ndvi).select('NDVI').median().clip(roi)
            
            # 5. ZONAL MEAN (Polygon Statistics)
            # We average all pixels inside our Polygon ROI
            stats = median_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=10 
            )

            actual_score = stats.get('NDVI').getInfo()

            # 6. --- NEW: BREACH RATIO ALGORITHM (Identifying Red Patches) ---
            # Define a threshold for "Critical Degradation" (0.2 is standard for soil/rock/snow)
            #
            degradation_threshold = 0.2


            # Create a mask where 1 = Breach (Red Patch), 0 = Healthy
            breach_mask = median_image.lt(degradation_threshold)
            mask_visual = breach_mask.visualize(palette=['black', 'white'])

            # Calculate the percentage of pixels that are in breach
            area_stats = breach_mask.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=10
            )
            breach_ratio = area_stats.get('NDVI').getInfo()
            breach_percentage = round(breach_ratio * 100, 2)

            # 6. FINAL VERDICT
            is_breach = actual_score < float(target_ndvi)

            res= {
                "status": "SUCCESS",
                "actual_ndvi": round(actual_score, 4),
                "target_ndvi": float(target_ndvi),
                "breach_area_percentage": f"{breach_percentage}%",
                "is_breach": is_breach,
                "verdict": "BREACH: ADJUST MARGIN UP" if is_breach else "COMPLIANT: APPLY DISCOUNT",
                "map_thumb_url": median_image.getThumbURL({
                    'min': 0, 'max': 1, 
                    'palette': ['red', 'yellow', 'green'],
                    'dimensions': 512
                }),
                "mask_thumb_url": mask_visual.getThumbURL({'dimensions': 512}),
                "analysis": f"Critical degradation detected in {breach_percentage}% of the site polygon."
            }
            print(res)
            return res
        except Exception as e:
            return {"status": "ERROR", "message": f"Verification Failure: {e}"}

# --- TEST BLOCK ---
if __name__ == "__main__":
    verifier = PlanetaryVerifier()
    # Test with your Success Coordinates
   
    result = verifier.verify_zonal_truth(61.62501, 24.32816, 0.75)
    print("\n--- FINAL AUDIT REPORT ---")
    print(result)