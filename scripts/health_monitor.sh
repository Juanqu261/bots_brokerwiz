#!/bin/bash
#
# BrokerWiz Health Monitor
# ========================
#
# Automated health monitoring script that runs via cron.
# Performs 6 health checks and logs alerts when issues are detected.
#
# Usage:
#   ./scripts/health_monitor.sh
#
# Cron setup (every 5 minutes):
#   */5 * * * * /path/to/brokerwiz/scripts/health_monitor.sh
#

set -e

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuración
LOG_DIR="$PROJECT_DIR/logs"
ALERT_LOG="$LOG_DIR/alerts.log"
WORKER_LOG="$LOG_DIR/worker.log"

# Umbrales
MAX_MINUTES_SINCE_LAST_JOB=10
MAX_ERROR_RATE_PERCENT=30
MIN_DISK_FREE_PERCENT=20
MAX_JOB_DURATION_MINUTES=30
MAX_QUEUE_DEPTH=100

# Cargar variables de entorno
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# ============================================================================
# Funciones de utilidad
# ============================================================================

log_alert() {
    local check_name="$1"
    local details="$2"
    local timestamp=$(date -Iseconds)
    echo "$timestamp ALERT $check_name: $details" >> "$ALERT_LOG"
}

send_email_alert() {
    local check_name="$1"
    local details="$2"
    
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$details" | mail -s "BrokerWiz Alert: $check_name" "$ALERT_EMAIL" 2>/dev/null || {
            echo "$(date -Iseconds) WARNING: Failed to send email alert" >> "$ALERT_LOG"
        }
    fi
}

send_webhook_alert() {
    local check_name="$1"
    local details="$2"
    
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST "$ALERT_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{\"check\": \"$check_name\", \"status\": \"failed\", \"details\": \"$details\", \"timestamp\": \"$(date -Iseconds)\"}" \
             --max-time 5 \
             --silent \
             --show-error 2>/dev/null || {
            echo "$(date -Iseconds) WARNING: Failed to send webhook alert" >> "$ALERT_LOG"
        }
    fi
}

# ============================================================================
# Health Checks
# ============================================================================

check_recent_activity() {
    # Check if last job completed within MAX_MINUTES_SINCE_LAST_JOB minutes
    
    if [ ! -f "$WORKER_LOG" ]; then
        return 1  # Fail if log doesn't exist
    fi
    
    # Get last completion timestamp
    last_completion=$(grep "completado exitosamente" "$WORKER_LOG" | tail -1 | cut -d'|' -f1 | xargs)
    
    if [ -z "$last_completion" ]; then
        return 1  # No completions found
    fi
    
    # Convert to epoch seconds
    last_completion_epoch=$(date -d "$last_completion" +%s 2>/dev/null || echo 0)
    current_epoch=$(date +%s)
    
    # Calculate age in minutes
    age_seconds=$((current_epoch - last_completion_epoch))
    age_minutes=$((age_seconds / 60))
    
    if [ $age_minutes -gt $MAX_MINUTES_SINCE_LAST_JOB ]; then
        return 1  # Too old
    fi
    
    return 0  # OK
}

check_error_rate() {
    # Check if error rate in last hour is below MAX_ERROR_RATE_PERCENT
    
    if [ ! -f "$WORKER_LOG" ]; then
        return 0  # Pass if log doesn't exist (no data)
    fi
    
    # Get timestamp from 1 hour ago
    one_hour_ago=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')
    
    # Count completions and failures in last hour
    completed=$(awk -v cutoff="$one_hour_ago" '$0 > cutoff && /completado exitosamente/ {count++} END {print count+0}' "$WORKER_LOG")
    failed=$(awk -v cutoff="$one_hour_ago" '$0 > cutoff && /completado con errores/ {count++} END {print count+0}' "$WORKER_LOG")
    
    total=$((completed + failed))
    
    if [ $total -eq 0 ]; then
        return 0  # No jobs in last hour, pass
    fi
    
    # Calculate error rate
    error_rate=$((failed * 100 / total))
    
    if [ $error_rate -gt $MAX_ERROR_RATE_PERCENT ]; then
        echo "$error_rate"  # Return error rate for alert message
        return 1  # Fail
    fi
    
    return 0  # OK
}

check_mqtt_broker() {
    # Check if MQTT broker is responsive
    
    # Try to connect with mosquitto_sub (timeout 2s)
    timeout 2 mosquitto_sub -h ${MQTT_HOST:-localhost} -p ${MQTT_PORT:-1883} -t '$SYS/broker/uptime' -C 1 >/dev/null 2>&1
    return $?
}

check_disk_space() {
    # Check if disk free space is above MIN_DISK_FREE_PERCENT
    
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    disk_free=$((100 - disk_usage))
    
    if [ $disk_free -lt $MIN_DISK_FREE_PERCENT ]; then
        echo "$disk_free"  # Return free percent for alert message
        return 1  # Fail
    fi
    
    return 0  # OK
}

check_stuck_workers() {
    # Check if any job has been running for more than MAX_JOB_DURATION_MINUTES
    
    if [ ! -f "$WORKER_LOG" ]; then
        return 0  # Pass if log doesn't exist
    fi
    
    # Find jobs that started but didn't complete
    # This is a simplified check - looks for recent "Recibido job" without matching completion
    
    # Get jobs received in last 2 hours
    two_hours_ago=$(date -d '2 hours ago' '+%Y-%m-%d %H:%M:%S')
    
    # Extract job IDs that were received
    received_jobs=$(awk -v cutoff="$two_hours_ago" '$0 > cutoff && /Recibido job:/ {
        match($0, /job: ([^ ]+)/, arr);
        if (arr[1]) print arr[1]
    }' "$WORKER_LOG" | sort -u)
    
    # Extract job IDs that completed
    completed_jobs=$(awk -v cutoff="$two_hours_ago" '$0 > cutoff && /(completado exitosamente|completado con errores|DLQ)/ {
        match($0, /Job ([^ ]+)/, arr);
        if (arr[1]) print arr[1]
    }' "$WORKER_LOG" | sort -u)
    
    # Find jobs that are still running
    stuck_count=0
    for job_id in $received_jobs; do
        if ! echo "$completed_jobs" | grep -q "^$job_id$"; then
            # Job is still running, check duration
            start_time=$(grep "Recibido job: $job_id" "$WORKER_LOG" | tail -1 | cut -d'|' -f1 | xargs)
            if [ -n "$start_time" ]; then
                start_epoch=$(date -d "$start_time" +%s 2>/dev/null || echo 0)
                current_epoch=$(date +%s)
                duration_minutes=$(( (current_epoch - start_epoch) / 60 ))
                
                if [ $duration_minutes -gt $MAX_JOB_DURATION_MINUTES ]; then
                    stuck_count=$((stuck_count + 1))
                fi
            fi
        fi
    done
    
    if [ $stuck_count -gt 0 ]; then
        echo "$stuck_count"  # Return count for alert message
        return 1  # Fail
    fi
    
    return 0  # OK
}

check_queue_depth() {
    # Check if queue depth is below MAX_QUEUE_DEPTH
    
    # Query MQTT broker for stored messages
    queue_depth=$(timeout 2 mosquitto_sub -h ${MQTT_HOST:-localhost} -p ${MQTT_PORT:-1883} -t '$SYS/broker/messages/stored' -C 1 2>/dev/null || echo "-1")
    
    if [ "$queue_depth" = "-1" ]; then
        return 0  # Pass if can't get queue depth (broker might be down, other check will catch it)
    fi
    
    if [ $queue_depth -gt $MAX_QUEUE_DEPTH ]; then
        echo "$queue_depth"  # Return depth for alert message
        return 1  # Fail
    fi
    
    return 0  # OK
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    local failed_checks=0
    
    # Check 1: Recent activity
    if ! check_recent_activity; then
        log_alert "recent_activity" "No job completed in last $MAX_MINUTES_SINCE_LAST_JOB minutes"
        send_email_alert "recent_activity" "No job completed in last $MAX_MINUTES_SINCE_LAST_JOB minutes"
        send_webhook_alert "recent_activity" "No job completed in last $MAX_MINUTES_SINCE_LAST_JOB minutes"
        failed_checks=$((failed_checks + 1))
    fi
    
    # Check 2: Error rate
    error_rate_result=$(check_error_rate)
    if [ $? -ne 0 ]; then
        log_alert "error_rate" "Error rate above $MAX_ERROR_RATE_PERCENT%: ${error_rate_result}%"
        send_email_alert "error_rate" "Error rate above $MAX_ERROR_RATE_PERCENT%: ${error_rate_result}%"
        send_webhook_alert "error_rate" "Error rate above $MAX_ERROR_RATE_PERCENT%: ${error_rate_result}%"
        failed_checks=$((failed_checks + 1))
    fi
    
    # Check 3: MQTT broker
    if ! check_mqtt_broker; then
        log_alert "mqtt_broker" "MQTT broker is not responsive"
        send_email_alert "mqtt_broker" "MQTT broker is not responsive"
        send_webhook_alert "mqtt_broker" "MQTT broker is not responsive"
        failed_checks=$((failed_checks + 1))
    fi
    
    # Check 4: Disk space
    disk_free_result=$(check_disk_space)
    if [ $? -ne 0 ]; then
        log_alert "disk_space" "Disk free space below $MIN_DISK_FREE_PERCENT%: ${disk_free_result}% free"
        send_email_alert "disk_space" "Disk free space below $MIN_DISK_FREE_PERCENT%: ${disk_free_result}% free"
        send_webhook_alert "disk_space" "Disk free space below $MIN_DISK_FREE_PERCENT%: ${disk_free_result}% free"
        failed_checks=$((failed_checks + 1))
    fi
    
    # Check 5: Stuck workers
    stuck_count_result=$(check_stuck_workers)
    if [ $? -ne 0 ]; then
        log_alert "stuck_workers" "$stuck_count_result job(s) running for more than $MAX_JOB_DURATION_MINUTES minutes"
        send_email_alert "stuck_workers" "$stuck_count_result job(s) running for more than $MAX_JOB_DURATION_MINUTES minutes"
        send_webhook_alert "stuck_workers" "$stuck_count_result job(s) running for more than $MAX_JOB_DURATION_MINUTES minutes"
        failed_checks=$((failed_checks + 1))
    fi
    
    # Check 6: Queue depth
    queue_depth_result=$(check_queue_depth)
    if [ $? -ne 0 ]; then
        log_alert "queue_depth" "Queue depth above $MAX_QUEUE_DEPTH: $queue_depth_result messages"
        send_email_alert "queue_depth" "Queue depth above $MAX_QUEUE_DEPTH: $queue_depth_result messages"
        send_webhook_alert "queue_depth" "Queue depth above $MAX_QUEUE_DEPTH: $queue_depth_result messages"
        failed_checks=$((failed_checks + 1))
    fi
    
    # Exit with appropriate code
    if [ $failed_checks -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

main
