mysqldump: [Warning] Using a password on the command line interface can be insecure.
-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: fastapiadmin
-- ------------------------------------------------------
-- Server version       8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `monitor_prometheus_job`
--

DROP TABLE IF EXISTS `monitor_prometheus_job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitor_prometheus_job` (
  `job_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Job 名称',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '描述',
  `is_enabled` tinyint(1) NOT NULL COMMENT '是否启用',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_prometheus_job_name` (`job_name`),
  KEY `ix_monitor_prometheus_job_creator_id` (`creator_id`),
  CONSTRAINT `monitor_prometheus_job_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Prometheus Job 配置';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `monitor_prometheus_endpoint`
--

DROP TABLE IF EXISTS `monitor_prometheus_endpoint`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitor_prometheus_endpoint` (
  `job_id` int NOT NULL,
  `endpoint` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Endpoint/Target，如 10.0.0.1:9100',
  `is_enabled` tinyint(1) NOT NULL COMMENT '是否启用',
  `scheme` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '协议',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '备注/描述',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_prometheus_job_endpoint` (`job_id`,`endpoint`),
  KEY `ix_monitor_prometheus_endpoint_job_id` (`job_id`),
  KEY `ix_monitor_prometheus_endpoint_creator_id` (`creator_id`),
  CONSTRAINT `monitor_prometheus_endpoint_ibfk_1` FOREIGN KEY (`job_id`) REFERENCES `monitor_prometheus_job` (`id`) ON DELETE CASCADE,
  CONSTRAINT `monitor_prometheus_endpoint_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=99 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Prometheus Endpoint 配置';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `monitor_prometheus_label`
--

DROP TABLE IF EXISTS `monitor_prometheus_label`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitor_prometheus_label` (
  `label_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签键',
  `label_value` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签值',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `endpoint_id` int NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '备注/描述',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_prometheus_endpoint_label` (`endpoint_id`,`label_key`),
  KEY `ix_monitor_prometheus_label_creator_id` (`creator_id`),
  KEY `ix_monitor_prometheus_label_endpoint_id` (`endpoint_id`),
  CONSTRAINT `fk_prometheus_label_endpoint` FOREIGN KEY (`endpoint_id`) REFERENCES `monitor_prometheus_endpoint` (`id`) ON DELETE CASCADE,
  CONSTRAINT `monitor_prometheus_label_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=87 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Prometheus Label 配置';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-05 15:27:59