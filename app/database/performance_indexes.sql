-- Performance Optimization Indexes for Property Search
-- These indexes improve search performance for large datasets

-- 1. Primary Search Index - Covers most common search patterns
-- This index supports filtering by approval status, property type, and sorting by creation date
CREATE INDEX IX_Properties_Search 
ON Properties (IsApproved, IsDeleted, IsRejected, IsDraft, PropertyType, CreatedAt DESC, Id)
INCLUDE (Name, MonthlyRent, City, Government, Description, NumberOfBedrooms, Furnished, Size, MinimumStay);

-- 2. Location-Based Search Index
-- Optimizes searches filtered by government or city
CREATE INDEX IX_Properties_Location 
ON Properties (Government, City) 
WHERE IsApproved = 1 AND IsDeleted = 0 AND IsRejected = 0 AND IsDraft = 0;

-- 3. Price-Based Search Index
-- Optimizes searches filtered by monthly rent
CREATE INDEX IX_Properties_Price 
ON Properties (MonthlyRent) 
WHERE IsApproved = 1 AND IsDeleted = 0 AND IsRejected = 0 AND IsDraft = 0;

-- 4. Furnished Status Index
-- Optimizes searches filtered by furnished status
CREATE INDEX IX_Properties_Furnished 
ON Properties (Furnished) 
WHERE IsApproved = 1 AND IsDeleted = 0 AND IsRejected = 0 AND IsDraft = 0;

-- 5. Property Amenities Index
-- Optimizes JOIN with PropertyAmenities table
CREATE INDEX IX_PropertyAmenities_PropertyId 
ON PropertyAmenities (PropertyId, Wifi, AirConditioning, Tv, Washer, Refrigerator, FreeParking);

-- 6. Rooms Index for Shared Properties
-- Optimizes searches for shared apartments (room-level pricing)
CREATE INDEX IX_Rooms_PropertyId 
ON Rooms (PropertyId, Month_rent, IsDeleted) 
WHERE IsDeleted = 0;

-- 7. Allowed Tenants Index
-- Optimizes searches filtered by tenant type and gender
CREATE INDEX IX_AllowedTenants_PropertyId 
ON AllowedTenants (PropertyId, AllowsStudents, AllowsWorkers, StudentGender, WorkerGender);

-- 8. Composite Index for Common Search Pattern
-- Combines location, price, and creation date for typical user searches
CREATE INDEX IX_Properties_CommonSearch 
ON Properties (Government, City, MonthlyRent, CreatedAt DESC, Id)
WHERE IsApproved = 1 AND IsDeleted = 0 AND IsRejected = 0 AND IsDraft = 0;

-- 9. Index for Cursor-Based Pagination
-- Specifically designed for cursor pagination using CreatedAt + Id
CREATE INDEX IX_Properties_CursorPagination 
ON Properties (CreatedAt DESC, Id) 
WHERE IsApproved = 1 AND IsDeleted = 0 AND IsRejected = 0 AND IsDraft = 0 AND PropertyType = 1;

-- 10. Full-Text Search Index (if using SQL Server Full-Text Search)
-- Enables efficient text search in property descriptions
-- CREATE FULLTEXT INDEX ON Properties(Description) KEY INDEX PK_Properties;

-- Note: After creating indexes, run UPDATE STATISTICS to ensure query optimizer uses them
-- UPDATE STATISTICS Properties WITH FULLSCAN;
-- UPDATE STATISTICS PropertyAmenities WITH FULLSCAN;
-- UPDATE STATISTICS Rooms WITH FULLSCAN;
-- UPDATE STATISTICS AllowedTenants WITH FULLSCAN;
